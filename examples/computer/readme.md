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
