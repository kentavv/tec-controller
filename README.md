# extech-ea15
Decode temperature measurements from an Extech EA15 thermocouple data logging thermometer. There's a good chance that the related thermometers, even with different number of probe inputs, have a similar protocol. Probably only need to change the number of measurements sent in each packet. I'm willing to add support for additional Extech thermometers sent to me to examine.

To disable the instrument turning off after 30 minutes of inactivity, hold the Enter key while turning power on or enable either the data logging or min-max mode. (Changing the mode is the only way to have a positive indication that auto power off is disabled.)

The temperature unit selected on the data logger is read, but to ensure uniformity, especially within downloaded measurements, all measurements are converted to C. Without doing this, changing the units during the data logging would cause the downloaded results to have multiple units. (Preserving the original units moght be preferred, and could be used to flag sections of the recorded data at the instrument.)

The data logger only reports the logging interval. The time of the measurements are not recorded. One is expected to write down the starting time. The timestamps on the downloaded data can then be shifted to the start time.

Manually logged measurements (quick press of Mem button) cannot be downloaded. Reviewing these (quick press of Read button followed by up or down buttons) are likely to stop serial data until normal run restarts (second quick press of Read button.)

Pressing the Hold button is also likely to block serial. In general, a new measurement is only sent over serial if the display updates.

Written August 6, 2020 by Kent A. Vander Velden kent.vandervelden@gmail.com

# References

[http://www.extech.com/products/resources/EA15_UM-en.pdf](http://www.extech.com/products/resources/EA15_UM-en.pdf)

[http://www.extech.com/products/resources/EA10_EA15_DS-en.pdf](http://www.extech.com/products/resources/EA10_EA15_DS-en.pdf)

[Comparison of thermocouple types](https://www.thermocoupleinfo.com/thermocouple-types.htm)
