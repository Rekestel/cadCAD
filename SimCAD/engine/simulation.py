from copy import deepcopy
from fn import _
from fn.op import foldr, call

class Executor(object):
    def __init__(self, behavior_ops):
        self.behavior_ops = behavior_ops

    # Data Type reduction
    def getBehaviorInput(self, step, sL, s, funcs):

        if len(self.behavior_ops) == 0:
            ops = [foldr(_ + _)]
        else:
            ops = self.behavior_ops[::-1]

        def getColResults(step, sL, s, funcs):
            return list(map(lambda f: f(step, sL, s), funcs))

        return foldr(call, getColResults(step, sL, s, funcs))(ops)

    def apply_env_proc(env_processes, state_dict, step):
        for state in state_dict.keys():
            if state in list(env_processes.keys()):
                state_dict[state] = env_processes[state](step)(state_dict[state])

    # remove / modify
    def exception_handler(self, f, m_step, sL, last_mut_obj, _input):
        try:
            return f(m_step, sL, last_mut_obj, _input)
        except KeyError:
            print("Exception")
            return f(m_step, sL, sL[-2], _input)


    def mech_step(self, m_step, sL, state_funcs, behavior_funcs, env_processes, t_step, run):
        last_in_obj = sL[-1]

        _input = self.getBehaviorInput(m_step, sL, last_in_obj, behavior_funcs)

        # print(sL)

        # *** add env_proc value here as wrapper function ***
        last_in_copy = dict([ self.exception_handler(f, m_step, sL, last_in_obj, _input) for f in state_funcs ])

        for k in last_in_obj:
            if k not in last_in_copy:
                last_in_copy[k] = last_in_obj[k]

        del last_in_obj

        #	make env proc trigger field agnostic
        Executor.apply_env_proc(env_processes, last_in_copy, last_in_copy['timestamp']) # mutating last_in_copy

        last_in_copy["mech_step"], last_in_copy["time_step"], last_in_copy['run'] = m_step, t_step, run
        # print(last_in_copy)
        sL.append(last_in_copy)
        del last_in_copy

        return sL


    def block_gen(self, states_list, configs, env_processes, t_step, run):
        m_step = 0
        states_list_copy = deepcopy(states_list)
        # remove copy
        genesis_states = states_list_copy[-1]
        genesis_states['mech_step'], genesis_states['time_step'] = m_step, t_step
        states_list = [genesis_states]

        m_step += 1
        for config in configs:
            s_conf, b_conf = config[0], config[1]
            states_list = self.mech_step(m_step, states_list, s_conf, b_conf, env_processes, t_step, run)
            m_step += 1

        t_step += 1

        return states_list


    # rename pipe
    def pipe(self, states_list, configs, env_processes, time_seq, run):
        time_seq = [x + 1 for x in time_seq]
        simulation_list = [states_list]
        for time_step in time_seq:
            pipe_run = self.block_gen(simulation_list[-1], configs, env_processes, time_step, run)
            _, *pipe_run = pipe_run
            simulation_list.append(pipe_run)

        return simulation_list


    # Del _ / head
    def simulation(self, states_list, configs, env_processes, time_seq, runs):
        pipe_run = []
        for run in range(runs):
            run += 1
            if run == 1:
                head, *tail = self.pipe(states_list, configs, env_processes, time_seq, run)
                head[-1]['mech_step'], head[-1]['time_step'], head[-1]['run'] = 0, 0, 0
                simulation_list = [head] + tail
                pipe_run += simulation_list
            else:
                transient_states_list = [pipe_run[-1][-1]]
                _, *tail = self.pipe(transient_states_list, configs, env_processes, time_seq, run)
                pipe_run += tail

        return pipe_run