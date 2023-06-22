---
date: 2023-06-21
categories:
  - writeups
authors:
  - silk
  - matt
tags:
  - hardware
---

# CyberSci Hardware Challenge

**Difficulty:** Medium/Hard

The objective of the challenge is to dump the firmware from the provided hardware badge and reverse engineer it. In theory this is quite easy, however it took quite some time to get familiar with the AVR architecture and instruction set.

*Hints: If you're just starting out, ask Jeff Bezos for help. If you're near the end, ask Jeff Bezos for help.*

## Process

### The Badge

![Picture of the hardware badge]()

Upon inital inspection we can see the board has been nicely labelled for us. There is also a small push button, a power switch, some LED's/resistors, and an IC chip present.

When powered on, the badge will cycle through different light patterns when the small push button is pressed. 

We are only intersted in the chip, as we know that the challenge must be hidden in the firmware.

![Picture of the ATTiny1614 Microchip]()

The chip has some small writing on the casing, and we can make out "ATMEL TINY1614N". Googling around for it quickly reveals the documentation (hosted on aws, hence the hint), which explains that we can interact with it via UPDI (the Unified Program and Debug Interface).

### What's UPDI?

Taken straight from the documentation: UPDI is a Microchip TM (formerly Atmel) proprietary interface for external programming and on-chip debugging of a device. 

It operates over a one-wire interface, so other than hooking up GND and VCC (the power supply), there is minimal setup required.

### Interfacing with the badge

Luckily, the challenge creator (Loudmouth Security) graciously connected the UPDI pinout into the single wire interface for us, so other than connecting GND and VCC we don't have to do much more for setup.

After conducting some research, tools such as ```avr-dude with jtag2updi``` and ```updiprog``` quickly became of interest as they seemed to be capable of dumping the firmware.

### First Attempt

Originally, it was thought that an Arduino Uno (or alike) could be converted into a TTL (aka serial) to USB adapter to enable communication with the chip.

After reading several guides of people looking to program various chips via UPDI, the following schematic seemed to be accurate.

```
                        VCC       (3.3v)        VCC
                         +-----------------------+
                         |                       |
 +---------------------+ |                       | +--------------------+
 | Serial Adapter      +-+      Resistor         +-+  AVR device        |
 |                     |      +----------+         |                    |
 |                  TX +------+ 1k OHM   +---------+ UPDI               |
 |                     |      +----------+    |    |                    |
 |                     |                      |    |                    |
 |                  RX +----------------------+    |                    |
 |                     |                           |                    |
 |                     +--+                     +--+                    |
 +---------------------+  |                     |  +--------------------+
                          +---------------------+
                         GND                   GND
```

However, communication using an Arduino was unsuccessful for a variety of reasons, mostly due to an issue with garbled input/output over the RX/TX lines. 

Rather than wasting time trying to mimic the required chipset, the following adapter can be purchased off Amazon for around $20 CAD.

[Link to adapter, completing another part of the hint](https://www.amazon.ca/dp/B07WX2DSVB?psc=1&ref=ppx_yo2ov_dt_b_product_details)

### Dumping the firmware

Once the adapter arrived and necessary drivers were installed, there were issues with ```avr-dude``` and ```updiprog```, so a switch to ```pymcuprog``` was made.

We are now left with the following setup and are ready to try dumping the firmware.

![Stephen Setup]()

To test the connection, UPDI offers "ping" like functionality.

**Note: ```pymcuprog``` is the recommend tool to use as many others are outdated and slow.**

```
pymcuprog ping -d attiny1614 -t uart -u COM6
Connecting to SerialUPDI
Pinging device...
Ping response: 1E9422
Done.
```
Hurray! We can now talk to the device.

We want to dump both the firmware (the code) and the SRAM (memory), as there may be valuable information in each.

```
pymcuprog read -m flash -d attiny1614 -t uart -u COM6 -f flash.hex
```
```
pymcuprog read -m internal_sram -d attiny1614 -t uart -u COM6 -f sram.hex
```

To confirm that the dump was correct, the firmware was dumped from another badge to compare.

The PCB from an old mini fridge had to be sacrificed to use a specific resistor, and made quite the interesting setup.

![PCB Setup]()

## Reversing the firmware

Before we can try reversing, we need to convert the files from intel hex into a binary format.

This can be done with the following tool:

```avr-objcopy -I ihex -O binary input.hex output.bin```

As mandated by CTF lore, strings was ran first and the following was spit out:

```JIGGYCIPHER{a1557d3801d7723f3d385111d85cd125625cc260ba76d3051a5de6ff24786b8fc70c1659aa4c4101b9151c8eef70d43P@8515a6642562ab9fP0403f276ba556a7429829433d2572484pf2585719d468964832ab1a258521f568f165c3ab1bead146ecd2de65a5d812b53ca5c168473bac895d4a8bc37390f860b11e6a6eb442c249180a9c337285455ab098d47b7264ec42bed7688d59dcdfddcf3d0de674356cbee....```

Quickly switching to a hex editor gives us the following:

```JIGGYCIPHER{a1557d3801d7723f3d385111d85cd125625cc260ba76d3051a5de6ff24786b8fc70c1659aa4c41b9151c8eef70d438515a6642562ab9f0403f276ba556a7429829433d2572484f2585719d468964832ab1a258521f568165c3ab1bead146ecd2de65a5d812b53ca5c168473bac895d4a8bc37390f860b11e6a6eb442c249180a9c337285455ab098d47b7264ec42bed7688d59dcdfddcf3d0de674356cbee22547e087c63be52013dc319600c4a4859788ab87349c6c81ea9598127f87093c148c1d3e94edea50132f324eaf5cc88b63b8fac20cf6}```

### This has evovled into a Rev/Crypto Challenge...

Any attempt to try and decode this using known ciphers fails, and performing frequency analysis yields no promising results.

Maybe there is some sort of encryption routine in the firmware!

### Ghidra to the rescue?

Ghidra does support the AVR architecture, however there is no direct support for the ATTINY1614 CPU.

After reading the documentation, we found that the language was `AVR8:Little Endian:16 Bit` and it was compiled with GCC (uses avr-libc).

The memory mapping was very messed up, and ghidra created lots of weird memory segments and bad instructions.

This is due to the fact that AVR uses a **Harvard architecture, meaning that the program code and memory are stored in seperate physical locations, and have completely different addresses**. (This is a nightmare for all pwn people, as it almost removes the ability to manipulate program flow/data.)

![Block Diagram]()

After importing the SRAM and EEPROM dumps and adjusting the memory mapping, the disassembly was still very hard to read, and static analysis was incredibly annoying to perform as it required switching back and forth between the different segments.

![Flash Diagram]()

### Static Analysis? Nah. Let's Emulate it!

There are few ways emulation can be done, however Cutter was used as it was super user friendly had required no setup.

[simavr](https://github.com/buserror/simavr) can also be used, but requires you to build/define the CPU/core for emulation.







