emacsCppComplete
================

Requirements
------------
* Emacs 2.2+
* Python 2.6+
* Pymacs (https://github.com/pinard/Pymacs/)
* gccxml 0.6
* Emacs plugin 'pos-tip.el' (http://www.emacswiki.org/emacs-en/PosTip)

Install
-------
Clone this repository, and put 'emacsCppComplete/' somewhere in your PYTHONPATH.

Then add something like this in your .emacs:

    (require 'pos-tip)
    (pymacs-load "emacsCppComplete")
    (global-set-key (kbd "M-p M-m") 'emacsCppComplete-check-word)
    (global-set-key (kbd "M-p M-u") 'emacsCppComplete-update-state)
    (global-set-key (kbd "M-p M-o") 'emacsCppComplete-command)
    (global-set-key (kbd "M-p M-l") 'emacsCppComplete-complete-type)


Usage
-----
The `check_word()` function will try to match your current word to possible completions. If there is only one possible completion it will autocomplete it. Else it will display possible completions.
It will need to have the completion information beforehand, so the first thing to do is to call `update_state()` with the assigned shortcut.
You can also directly find all completions for a type by using the complete_type() function.

.lemacs 
-------
.lemacs files are little hacks to add some include directories. When parsing your c++ file, emacsCppComplete will look for `.lemacs` file in parent directories and use the info there to enchance the completion. For example, and only feature for now, is to give paths to the program, which will add them in gcc as include paths(-I).
Example .lemacs:
    [include]
    ./Math/publicInterfaces
    ./Raytracer/publicInterfaces
    ./Objects/publicInterfaces
    ./Image/publicInterfaces

It might be a good idea to change the name of this file... 