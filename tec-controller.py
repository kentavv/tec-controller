#!/usr/bin/env python

# Copyright 2020 Kent A. Vander Velden <kent.vandervelden@gmail.com>
#
# If you use this software, please consider contacting me. I'd like to hear
# about your work.
#
# This file is part of TEC-controller
#
# Please see LICENSE for limitations on use.

import sys
import time

import matplotlib.pyplot as plt
import vxi11

import extech_ea15

# If you encounter an error about not being able to use the TkInter matplotlib backend
# or unable to load the tkinter module, try the following. (TkInter cannot be installed
# by pipenv.)
#   sudo apt-get install python3-tk

plt.ion()

ps_ip = '192.168.1.144'


def main(dev_fn):
    def decode(v):
        return f'{v["dt"]} : {v["t1"]} : {v["t2"]} : {v["type"]} : {v["valid"]}'

    with extech_ea15.ExtechEA15Threaded(dev_fn) as ea15:
        instr = vxi11.Instrument(ps_ip)
        idn = instr.ask('*IDN?')
        print(idn)
        if not idn.startswith('RIGOL TECHNOLOGIES,DP832'):
            print('Unknown instrument:', idn)
            sys.exit(1)
        instr.write('*RST')

        # instr.write('CONF:VOLT:DC AUTO,DEF')
        # instr.write('CONF:VOLT:DC 1,0.001')
        # instr.write('CONF:VOLT:AC 10,0.001')
        # instr.write('VOLT:AC:BAND 200')
        # instr.write('TRIG:DEL .005')

        # read n values with a small delay between each reading
        def sample(n=1, scale=10.):
            rv = []
            if instr is not None:
                for i in range(n):
                    if i > 0:
                        time.sleep(.05)
                    rv += [instr.ask('READ?')]
                rv = [float(x) * scale for x in rv]
            else:
                rv = [-1.] * n
            return rv

        while not ea15.q.empty():
            v = ea15.q.get()
            print(decode(v))

        while not ea15.q2.empty():
            v2_ = ea15.q2.get()
            for j, v2 in enumerate(v2_):
                sps, lst = v2
                print(f'Datalog set {j + 1} with {len(lst)} records, sampled every {sps} seconds')
                for i, v in enumerate(lst):
                    v['dt'] = i * sps
                    print(f'{j + 1:02d} : {i + 1:04d} : {decode(v)}')

        time.sleep(.5)


if __name__ == "__main__":
    dev_fn = extech_ea15.find_dev('usb-Prolific_Technology_Inc._USB-Serial_Controller')
    if not dev_fn:
        print('No device found')
    else:
        print('Using device:', dev_fn)
    #     main(dev_fn)

    instr = vxi11.Instrument(ps_ip)
    idn = instr.ask('*IDN?')
    print(idn)
    if not idn.startswith('RIGOL TECHNOLOGIES,DP832'):
        print('Unknown instrument:', idn)
        sys.exit(1)

    try:
        if False:
            instr.write('*RST')
            instr.write('*CLS')
            # time.sleep(1)

            # instr.write(':OUTP:TRAC CH2,OFF')
            # instr.write(':OUTP:TRAC CH1,OFF')
            # print(instr.ask(':OUTP:TRAC? CH1'))
            # print(instr.ask(':OUTP:TRAC? CH2'))

            # instr.write(':SYST:ONOFFS OFF')

            instr.write(':APPL CH1,12,1')
            instr.write(':APPL CH2,12,1')

            print(instr.ask(':SOUR1:VOLT?'))
            print(instr.ask(':SOUR2:VOLT?'))
            print(instr.ask(':SOUR1:CURR?'))
            print(instr.ask(':SOUR2:CURR?'))

            instr.write(':OUTP CH1,ON')
            instr.write(':OUTP CH2,ON')
            print(instr.ask(':OUTP? CH1'))
            print(instr.ask(':OUTP? CH2'))

            for i in range(1, 6 + 1):
                print('\n----------', i)

                ch1_i = i / 2 - .2
                ch2_i = i / 2 + .2
                print(ch1_i, ch2_i)

                instr.write(f':SOUR1:CURR {ch1_i}')
                instr.write(f':SOUR2:CURR {ch2_i}')
                print(instr.ask(':SOUR1:CURR?'))
                print(instr.ask(':SOUR2:CURR?'))

                time.sleep(2)

                ch1_meas = [float(x) for x in instr.ask(':MEAS:ALL? CH1').split(',')]
                ch2_meas = [float(x) for x in instr.ask(':MEAS:ALL? CH2').split(',')]
                total_i = ch1_meas[1] + ch2_meas[1]
                total_w = ch1_meas[2] + ch2_meas[2]
                print(f'CH1: {ch1_meas}  CH2: {ch2_meas}')
                print(f'total: {total_i:.04} A  {total_w:.04} W')

                time.sleep(2)

        fig, axs_ = plt.subplots(3, 3, sharex=True)
        axs = {'err': axs_[0][0],
               't1': axs_[0][1],
               't2': axs_[0][2],

               'p': axs_[1][0],
               'i': axs_[1][1],
               'd': axs_[1][2],

               'i_raw': axs_[2][0],
               'i_ps': axs_[2][1]
               }

        x = []
        ys = {k: [] for k in axs}

        lines = {k: axs[k].plot(x, ys[k], 'r-', label=k)[0] for k in axs}

        axs['err'].set_ylabel('err [C]')
        axs['t1'].set_ylabel('t1 [C]')
        axs['t2'].set_ylabel('t2 [C]')

        axs['p'].set_ylabel('p [A]')
        axs['i'].set_ylabel('i [A]')
        axs['d'].set_ylabel('d [A]')

        axs['i_raw'].set_ylabel('I_raw [A]')
        axs['i_ps'].set_ylabel('I_ps [A]')

        fig.add_subplot(111, frameon=False)
        # hide tick and tick label of the big axis
        plt.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)
        plt.xlabel("time [s]")
        # plt.ylabel("common Y")

        # for ax in axs_.flat:
        #     ax.set(xlabel='time [s]')
        #     # ax.label_outer()

        target_temp = -1
        axs['err'].axhline(0)
        target_line = axs['t1'].axhline(target_temp)

        with extech_ea15.ExtechEA15Threaded(dev_fn) as ea15:
            instr.write(':APPL CH1,12,1')
            instr.write(':APPL CH2,12,1')
            instr.write(':APPL CH2,5,1')

            print(instr.ask(':SOUR1:VOLT?'))
            print(instr.ask(':SOUR2:VOLT?'))
            print(instr.ask(':SOUR3:VOLT?'))
            print(instr.ask(':SOUR1:CURR?'))
            print(instr.ask(':SOUR2:CURR?'))
            print(instr.ask(':SOUR3:CURR?'))

            instr.write(':OUTP CH1,ON')
            instr.write(':OUTP CH2,ON')
            instr.write(':OUTP CH3,OFF')
            print(instr.ask(':OUTP? CH1'))
            print(instr.ask(':OUTP? CH2'))
            print(instr.ask(':OUTP? CH3'))

            target_i = 2

            time.sleep(2)

            kp = 10
            ki = 1 / 10
            kd = .02

            err_lst = []
            term_i = 0
            p_err = None
            dt = None
            st = time.time()
            while True:
                cc = [float(x) for x in open('config.txt').read().split()]
                target_temp, kp, ki, fd = cc

                st = time.time()
                # print('\n----------', target_i)

                # ch1_i = target_i / 2 - .2
                # ch2_i = target_i / 2 + .2
                ch1_i = target_i / 2
                ch2_i = target_i / 2

                if target_i >= 0:
                    instr.write(f':SOUR1:CURR {ch1_i}')
                    instr.write(f':SOUR2:CURR {ch2_i}')
                    instr.write(':OUTP CH3,OFF')
                elif target_i < 0:
                    instr.write(f':SOUR1:CURR {-ch1_i}')
                    instr.write(f':SOUR2:CURR {-ch2_i}')
                    instr.write(':OUTP CH3,ON')

                # print('CH1(set):', instr.ask(':SOUR1:CURR?'), ' CH2(set):', instr.ask(':SOUR2:CURR?'))

                ch1_meas = [float(x) for x in instr.ask(':MEAS:ALL? CH1').split(',')]
                ch2_meas = [float(x) for x in instr.ask(':MEAS:ALL? CH2').split(',')]
                total_i = ch1_meas[1] + ch2_meas[1]
                total_w = ch1_meas[2] + ch2_meas[2]


                # print(f'CH1: {ch1_meas}  CH2: {ch2_meas}')
                # print(f'total: {total_i:.04} A  {total_w:.04} W')

                def decode(v):
                    return f'{v["dt"]} : {v["t1"]} : {v["t2"]} : {v["type"]} : {v["valid"]}'


                # print('----')
                while True:
                    v = None
                    while not ea15.q.empty():
                        v = ea15.q.get()
                    if v is not None:
                        # print(decode(v))

                        t1 = v['t1'].C()
                        t2 = v['t2'].C()
                        err = t1 - target_temp
                        dt = time.time() - st

                        err_lst += [err]

                        if p_err is not None:
                            term_p = kp * err
                            term_i += ki * err
                            term_d = kd * (err - p_err) / dt
                            pid_i_raw = term_p + term_i + term_d
                            pid_i = pid_i_raw
                            if pid_i < -6:
                                pid_i = -6
                            elif pid_i > 6:
                                pid_i = 6
                            print(f'target:{target_temp:.01f}C, cur:{t1:.01f}C, err:{err:.01f}C, t2:{t2:.01f}, total_i:{total_i:.02f}A, '
                                  f'target_i:{target_i:.02f}A, pid_i_raw:{pid_i_raw:.02f}A, pid_i:{pid_i:.02f}A, kp:{kp:.02f}, term_p:{term_p:.04f}, term_i:{term_i:.04f}, '
                                  f'kd:{kd:.02f}, err:{err:.04f}, p_err:{p_err:.04f}, err-p_err:{err - p_err:.04f}, dt:{dt:.04f}, '
                                  f'(err-p_err)/dt:{(err - p_err) / dt:.04f}, term_d:{term_d:.04f}')
                            target_i = pid_i

                            ys['err'] += [err]
                            ys['t1'] += [v['t1'].C()]
                            ys['t2'] += [v['t2'].C()]

                            ys['p'] += [term_p]
                            ys['i'] += [term_i]
                            ys['d'] += [term_d]

                            ys['i_raw'] += [pid_i_raw]
                            ys['i_ps'] += [pid_i]

                            if x == []:
                                t0 = v['dt']
                            x += [(v['dt'] - t0).total_seconds()]

                            target_line.set_ydata([target_temp, target_temp])

                            # print('x:', x)
                            for k in axs:
                                # print(f'y{k}:', ys[k])
                                lines[k].set_xdata(x)
                                lines[k].set_ydata(ys[k])

                            for k in axs:
                                axs[k].relim()
                                axs[k].autoscale_view()

                            fig.canvas.draw()
                            fig.canvas.flush_events()

                        p_err = err

                        break

                        # if len(err_lst) > 10:
                        #     term_i += ki * err
                        #     # pid_i = kp * err + ki * sum(err_lst) + kd * (err_lst[0] - err_lst[-1])
                        #     pid_i = kp * err + term_i + kd * (err_lst[0] - err_lst[-1])
                        #     if pid_i < 0:
                        #         pid_i = 0
                        #     elif pid_i > 6:
                        #         pid_i = 6
                        #     print(f'target:{target_temp:.01f}C, cur:{t1:.01f}C, err:{err:.01f}C, t2:{t2:.01f}, total_i:{total_i:.02f}A, target_i:{target_i:.02f}A, pid_i:{pid_i:.02f}A')
                        #     target_i = pid_i
                        # else:
                        #     print(f'target:{target_temp:.01f}C, cur:{t1:.01f}C, err:{err:.01f}C, t2:{t2:.01f}, total_i:{total_i:.02f}A, target_i:{target_i:.02f}A')
                        # break

                time.sleep(2)
    except KeyboardInterrupt:
        instr.write(f':SOUR1:CURR .5')
        instr.write(f':SOUR2:CURR .5')
        instr.write(':OUTP CH1,OFF')
        instr.write(':OUTP CH2,OFF')
        instr.write(':OUTP CH3,OFF')
