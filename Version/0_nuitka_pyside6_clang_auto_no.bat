nuitka --standalone ^
    --enable-plugin=pyside6 ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=icon.ico ^
    --include-data-files=icon.ico=icon.ico ^
    --include-module=pypinyin ^
    --include-data-dir="D:\Program Files\Python310\lib\site-packages\pypinyin"=pypinyin ^
    --include-module=threading ^
    --include-module=concurrent.futures ^
    --include-module=concurrent.futures.thread ^
    --include-module=concurrent.futures.process ^
    --include-module=queue ^
    --include-module=weakref ^
    --include-package-data=pinyin ^
    --follow-imports ^
    --jobs=4 ^
    --clang ^
    --remove-output ^
    --output-dir=build_output ^
    your_script.py

