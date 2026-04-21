#!/usr/bin/env python3
"""
Quick setup guide - Run this to execute the voice changer
"""

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                 🎙️  HOW TO RUN THE VOICE CHANGER 🎙️                      ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

⚠️  FIX: Python command not found

SOLUTION: Use one of these methods to run the project:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 1: Use the run script (EASIEST) ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  cd /Users/arpitjindal/SNS\ Project
  ./run.sh

Or directly:

  /Users/arpitjindal/SNS\ Project/run.sh


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 2: Use python3 directly
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  cd /Users/arpitjindal/SNS\ Project
  python3 main.py


Or:

  python3 /Users/arpitjindal/SNS\ Project/main.py


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 3: Use full path (most explicit)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \\
    /Users/arpitjindal/SNS\ Project/main.py


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 4: Create an alias (ONE-TIME SETUP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add this to your ~/.zshrc or ~/.bash_profile:

  alias python=/Library/Frameworks/Python.framework/Versions/3.13/bin/python3

Then reload:

  source ~/.zshrc   # or source ~/.bash_profile

Now you can use: python main.py


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 RECOMMENDED: Use Method 1 (./run.sh)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The run.sh script is already created and ready to use:

  cd "/Users/arpitjindal/SNS Project"
  ./run.sh

That's it! The voice changer will start immediately.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ONCE IT'S RUNNING - KEYBOARD CONTROLS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1-4    Select effect (Passthrough / Echo / Robot / Pitch)
  g      Toggle noise gate ON/OFF
  +/-    Adjust noise gate threshold
  v      Toggle visualization
  d      Show performance statistics
  ?      Show menu
  q      Quit


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 QUICK START:

  1. Open terminal
  2. cd /Users/arpitjindal/SNS\ Project
  3. ./run.sh
  4. Press 1-4 to try different effects
  5. Press 'q' to quit

That's all! Enjoy! 🎙️✨

╚════════════════════════════════════════════════════════════════════════════╝
""")
