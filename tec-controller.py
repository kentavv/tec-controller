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

import matplotlib
import vxi11
from PyQt5 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import extech_ea15

ps_ip = '192.168.1.144'

matplotlib.use('Qt5Agg')


class TEC_Controller:
    def __init__(self):
        self.config_fn = 'config.txt'

        self.target_temp = 22.5
        self.kp = 2
        self.ki = .002
        self.kd = .5

        self.max_i = 6

        self.x = []
        self.ys = {k: [] for k in ['err', 't1', 't2',
                                   'p', 'i', 'd',
                                   'i_raw', 'i_ps']}

        self.load_config()

        self.dev_fn = extech_ea15.find_dev('usb-Prolific_Technology_Inc._USB-Serial_Controller')
        if not self.dev_fn:
            print('No device found')
        else:
            print('Using device:', self.dev_fn)
        #     main2(dev_fn)

        self.ea15 = extech_ea15.ExtechEA15Threaded(self.dev_fn, timeformat='dt')
        self.ea15.run()

        self.instr = vxi11.Instrument(ps_ip)
        idn = self.instr.ask('*IDN?')
        print(idn)
        if not idn.startswith('RIGOL TECHNOLOGIES,DP832'):
            print('Unknown instrument:', idn)
            sys.exit(1)

        self.target_i = .5

        self.err_lst = []
        self.term_i = 0
        self.p_err = None
        self.t0 = None
        self.st = None
        self.t0 = None
        self.total_i = 0
        self.total_w = 0
        self.target_i = 0

    def __del__(self):
        if self.instr is not None:
            self.instr.write(f':SOUR1:CURR .5')
            self.instr.write(f':SOUR2:CURR .5')
            self.instr.write(':OUTP CH1,OFF')
            self.instr.write(':OUTP CH2,OFF')
            self.instr.write(':OUTP CH3,OFF')

    def save_config(self):
        with open(self.config_fn, 'w') as f:
            print(f'{self.target_temp} {self.kp} {self.ki} {self.kd}', file=f)

    def load_config(self):
        try:
            cc = [float(x) for x in open(self.config_fn).read().split()]
            self.target_temp, self.kp, self.ki, self.kd = cc
        except FileNotFoundError:
            print(f'Config {self.config_fn} not found, leaving parameters unchanged.')

    def setup(self):
        self.instr.write('*RST')
        self.instr.write('*CLS')

        # self.instr.write(':OUTP:TRAC CH2,OFF')
        # self.instr.write(':OUTP:TRAC CH1,OFF')
        # print(self.instr.ask(':OUTP:TRAC? CH1'))
        # print(self.instr.ask(':OUTP:TRAC? CH2'))

        # instr.write(':SYST:ONOFFS OFF')

        self.instr.write(':APPL CH1,12,1')
        self.instr.write(':APPL CH2,12,1')
        self.instr.write(':APPL CH3,5,1')

        print(self.instr.ask(':SOUR1:VOLT?'))
        print(self.instr.ask(':SOUR2:VOLT?'))
        print(self.instr.ask(':SOUR3:VOLT?'))
        print(self.instr.ask(':SOUR1:CURR?'))
        print(self.instr.ask(':SOUR2:CURR?'))
        print(self.instr.ask(':SOUR3:CURR?'))

        self.instr.write(':OUTP CH1,ON')
        self.instr.write(':OUTP CH2,ON')
        self.instr.write(':OUTP CH3,OFF')
        print(self.instr.ask(':OUTP? CH1'))
        print(self.instr.ask(':OUTP? CH2'))
        print(self.instr.ask(':OUTP? CH3'))

    def step(self):
        def decode(v):
            return f'{v["dt"]} : {v["t1"]} : {v["t2"]} : {v["type"]} : {v["valid"]}'

        v = None
        while not self.ea15.q.empty():
            v = self.ea15.q.get()
        if v is None:
            print('Empty EA15 packet')
            return

        # print(decode(v))

        t1 = v['t1'].C()
        t2 = v['t2'].C()
        if self.t0 is None:
            self.t0 = v['dt']
            self.st = v['dt']
        t = (v['dt'] - self.t0).total_seconds()
        dt = (v['dt'] - self.st).total_seconds()

        err = t1 - self.target_temp
        self.err_lst += [err]

        ch1_i = self.target_i / 2
        ch2_i = self.target_i / 2

        if self.target_i >= 0:
            self.instr.write(f':SOUR1:CURR {ch1_i}')
            self.instr.write(f':SOUR2:CURR {ch2_i}')
            self.instr.write(':OUTP CH3,OFF')
        elif self.target_i < 0:
            self.instr.write(f':SOUR1:CURR {-ch1_i}')
            self.instr.write(f':SOUR2:CURR {-ch2_i}')
            self.instr.write(':OUTP CH3,ON')

        # print('CH1(set):', instr.ask(':SOUR1:CURR?'), ' CH2(set):', instr.ask(':SOUR2:CURR?'))

        ch1_meas = [float(x) for x in self.instr.ask(':MEAS:ALL? CH1').split(',')]
        ch2_meas = [float(x) for x in self.instr.ask(':MEAS:ALL? CH2').split(',')]
        ch3_meas = [float(x) for x in self.instr.ask(':MEAS:ALL? CH3').split(',')]
        self.total_i = ch1_meas[1] + ch2_meas[1]
        self.total_w = ch1_meas[2] + ch2_meas[2]

        # print(f'CH1: {ch1_meas}  CH2: {ch2_meas}')
        # print(f'total: {self.total_i:.04} A  {self.total_w:.04} W')

        # print('----')

        if self.p_err is not None:
            term_p = self.kp * err
            self.term_i += self.ki * dt * err
            term_d = self.kd * (err - self.p_err) / dt
            pid_i_raw = term_p + self.term_i + term_d
            pid_i = pid_i_raw
            if pid_i < -self.max_i:
                pid_i = -self.max_i
            elif pid_i > self.max_i:
                pid_i = self.max_i
            delta_t = abs(t1 - t2)
            try:
                delta_eff = delta_t / self.total_w
            except ZeroDivisionError:
                delta_eff = float('inf')

            terms = [f't:{t:.02f}s ',
                     f'err:{err:.01f}C',
                     f'term_p:{term_p:.04f}A',
                     f'term_i:{self.term_i:.04f}A',
                     f'term_d:{term_d:.04f}A',
                     f'v1:{ch1_meas[0]:.03f}V',
                     f'v2:{ch2_meas[0]:.03f}V',
                     f'v3:{ch3_meas[0]:.03f}V',
                     f'i1:{ch1_meas[1]:.03f}A',
                     f'i2:{ch2_meas[1]:.03f}A',
                     f'i3:{ch3_meas[1]:.03f}A',
                     f'p1:{ch1_meas[2]:.03f}W',
                     f'p2:{ch2_meas[2]:.03f}W',
                     f'p3:{ch3_meas[2]:.03f}W',
                     f'target:{self.target_temp:.01f}C',
                     f't1:{t1:.01f}C',
                     f't2:{t2:.01f}S',
                     f'delta_t:{delta_t:.01f}C',
                     f'total_w:{self.total_w:.01f}W',
                     f'delta_eff:{delta_eff:.01f}C/W',
                     f'total_i:{self.total_i:.02f}A',
                     f'target_i:{self.target_i:.02f}A',
                     f'pid_i_raw:{pid_i_raw:.02f}A',
                     f'pid_i:{pid_i:.02f}A',
                     f'ki:{self.ki:.02f}AS/C',
                     f'kp:{self.kp:.02f}A/C',
                     f'kd:{self.kd:.02f}A/S',
                     f'err:{err:.04f}C',
                     f'p_err:{self.p_err:.04f}C',
                     f'err-p_err:{err - self.p_err:.04f}C',
                     f'dt:{dt:.04f}S',
                     f'(err-p_err)/dt:{(err - self.p_err) / dt:.04f}C/S'
                     ]
            print(', '.join(terms))

            self.target_i = pid_i

            self.ys['err'] += [err]
            self.ys['t1'] += [v['t1'].C()]
            self.ys['t2'] += [v['t2'].C()]

            self.ys['p'] += [term_p]
            self.ys['i'] += [self.term_i]
            self.ys['d'] += [term_d]

            self.ys['i_raw'] += [pid_i_raw]
            self.ys['i_ps'] += [pid_i]

            self.x += [t]

        self.p_err = err
        self.st = v['dt']


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        axs_ = fig.subplots(3, 3, sharex='all')
        super(MplCanvas, self).__init__(fig)

        self.axs = {'err': axs_[0][0],
                    't1': axs_[0][1],
                    't2': axs_[0][2],

                    'p': axs_[1][0],
                    'i': axs_[1][1],
                    'd': axs_[1][2],

                    'i_raw': axs_[2][0],
                    'i_ps': axs_[2][1]
                    }

        self.x = []
        self.ys = {k: [] for k in self.axs}

        self.lines = {k: self.axs[k].plot(self.x, self.ys[k], 'r-', label=k)[0] for k in self.axs}

        self.axs['err'].set_ylabel('err [C]')
        self.axs['t1'].set_ylabel('t1 [C]')
        self.axs['t2'].set_ylabel('t2 [C]')

        self.axs['p'].set_ylabel('p [A]/[C]')
        self.axs['i'].set_ylabel('i [A]/([C][s])')
        self.axs['d'].set_ylabel('d [A][s]/[C]')

        self.axs['i_raw'].set_ylabel('I_raw [A]')
        self.axs['i_ps'].set_ylabel('I_ps [A]')

        self.target_line = self.axs['t1'].axhline(0)

        # To create a common x-label, overlay an empty graph over the sub-graphs
        a = fig.add_subplot(111, frameon=False)
        a.set_xlabel("Time [s]")
        a.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)


class TEC_Window(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        self.tec = TEC_Controller()
        self.tec.setup()

        super().__init__(*args, **kwargs)
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QHBoxLayout(self._main)

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        layout.addWidget(self.canvas)

        self.xdata = []
        self.ydata = []

        self.canvas.target_line.set_ydata([self.tec.target_temp, self.tec.target_temp])

        layout2 = QtWidgets.QVBoxLayout()
        layout.addLayout(layout2)

        self.inputs = {}

        def aa(vn, s, v):
            layout3 = QtWidgets.QHBoxLayout()

            label = QtWidgets.QLabel(s, self)
            label.setFixedWidth(120)
            layout3.addWidget(label)
            self.inputs[vn] = QtWidgets.QLineEdit(v, self)
            self.inputs[vn].setFixedWidth(100)
            layout3.addWidget(self.inputs[vn])
            # button.clicked.connect(lambda: self.clear_graph())

            return layout3

        layout2.addLayout(aa('target_temp', 'Target temp [C]', str(self.tec.target_temp)))
        layout2.addLayout(aa('Kp', 'Kp [A]/[C]', str(self.tec.kp)))
        layout2.addLayout(aa('Ki', 'Ki [A]/([C][s])', str(self.tec.ki)))
        layout2.addLayout(aa('Kd', 'Kd [A][s]/[C]', str(self.tec.kd)))

        button = QtWidgets.QPushButton('Set PID', self)
        layout2.addWidget(button)
        button.clicked.connect(lambda: self.set_pid())
        button.setFixedSize(button.sizeHint())

        button = QtWidgets.QPushButton('Reset I_term', self)
        layout2.addWidget(button)
        button.clicked.connect(lambda: self.reset_i())
        button.setFixedSize(button.sizeHint())

        button = QtWidgets.QPushButton('Clear graph', self)
        layout2.addWidget(button)
        button.clicked.connect(lambda: self.clear_graph())
        button.setFixedSize(button.sizeHint())

        # self.update_plot()

        # Setup a timer to trigger the redraw by calling update_plot.
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tec.step)
        self.timer.start()

        # Setup a timer to trigger the redraw by calling update_plot.
        self.timer2 = QtCore.QTimer()
        self.timer2.setInterval(100)
        self.timer2.timeout.connect(self.update_plot)
        self.timer2.start()

        self.resize(1920, 1080)
        self.show()

    def clear_graph(self):
        self.tec.x = []
        for k in self.tec.ys:
            self.tec.ys[k] = []

    def set_pid(self):
        target_temp = float(self.inputs['target_temp'].text())
        self.tec.target_temp = target_temp
        self.tec.kp = float(self.inputs['Kp'].text())
        self.tec.ki = float(self.inputs['Ki'].text())
        self.tec.kd = float(self.inputs['Kd'].text())

        self.tec.save_config()

        self.canvas.target_line.set_ydata([target_temp, target_temp])

    def reset_i(self):
        self.tec.term_i = 0

    def update_plot(self):
        for k, v in self.tec.ys.items():
            self.canvas.lines[k].set_xdata(self.tec.x)
            self.canvas.lines[k].set_ydata(v)

        for k, v in self.canvas.axs.items():
            v.relim()
            v.autoscale_view()

        self.canvas.draw()
        self.canvas.flush_events()


def main():
    app = QtWidgets.QApplication(sys.argv)
    try:
        w = TEC_Window()
        app.exec_()
    except KeyboardInterrupt:
        del w.tec


if __name__ == "__main__":
    main()
