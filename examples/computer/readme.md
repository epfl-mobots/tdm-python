# Examples of programs running on the computer

## runprogram.py

Create a connection to the tdm, lock the first robot, compile an Aseba program whose source code is in a string and run it. The program is left running unattended.

This is the recommended way to run a program with tdmclient.

## runprogram0.py

Create a connection to the tdm and use a state machine to lock the first node, send a program and run it.

This shows how to use low-level communication with the tdm to run a program. When it's possible, using higher-level methods such as in `runprogram.py` is recommended.

## runprogram1.py

Create a connection to the tdm, lock the first robot, compile an Aseba program whose source code is in a string and run it using lower-level methods than `runprogram.py`.

## events.py

Create a connection to the tdm, lock the first robot, compile an Aseba program whose source code is in a string and run it. The Thymio program sends events to the computer. These events are received and displayed.

## sound.py

Demonstration of running a one-line program to call a native function. Contrary to variables which can be observed or changed directly, native functions can be executed only with a program running on the Thymio. This program plays one of the 9 system sounds.
