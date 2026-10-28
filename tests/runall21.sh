#!/bin/bash
cd /workspace
export GST_PLUGIN_PATH=/workspace/wkdeps/root/usr/lib/x86_64-linux-gnu/gstreamer-1.0
for t in test_game_v9 test_friends_v9 test_subjects_v9 test_version_v21 test_about_v9 test_v10_save test_v11_hints test_v11_layout test_v12_screens test_v12_layout test_v13 test_v14 test_v15 test_v16 test_v17 test_v18 test_v19 test_v20 test_v21; do
 ( timeout 900 pwenv/bin/python -u times-tables-quest/$t.py > v9tmp/v21-$t.log 2>&1; echo EXIT $? >> v9tmp/v20-$t.log ) &
done
wait
echo ALLDONE
