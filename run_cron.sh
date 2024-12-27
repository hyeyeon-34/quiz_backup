#!/bin/bash
echo "Script started at $(date)" >> /Users/hyeyeon/Desktop/quiz/debug_log.txt
source /Users/hyeyeon/Desktop/quiz/quiz/bin/activate
echo "Virtual environment activated" >> /Users/hyeyeon/Desktop/quiz/debug_log.txt
/Users/hyeyeon/Desktop/quiz/quiz/bin/python /Users/hyeyeon/Desktop/quiz/mongodb.py create_zes >> /Users/hyeyeon/Desktop/quiz/debug_log.txt 2>&1
echo "Script finished at $(date)" >> /Users/hyeyeon/Desktop/quiz/debug_log.txt
