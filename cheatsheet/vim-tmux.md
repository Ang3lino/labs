# Vim & Tmux — Exam Essentials

> ponytail: Default config only. No plugins. Pareto 20% that covers 80% of exam usage.

## Vim

### Movement

```
h j k l          ← ↓ ↑ →
w / b            Next / prev word
0 / $            Start / end of line
gg / G           Top / bottom of file
:<n>             Go to line n
%                Jump to matching bracket
```

### Editing

```
i                Insert before cursor
a                Insert after cursor
o / O            New line below / above
x                Delete char
dd               Delete line
yy               Copy line
p / P            Paste below / above
u                Undo
Ctrl+r           Redo
.                Repeat last action
```

### Visual Mode

```
v                Character select
V                Line select
Ctrl+v           Block select (columns)
d                Delete selected
y                Yank selected
>  / <           Indent / unindent selected
```

### Search & Replace

```
/pattern         Search forward
n / N            Next / prev match
:%s/old/new/g    Replace all in file
:s/old/new/g     Replace all in current line
```

### Multi-file

```
:e file.yaml     Open file
:w               Save
:wq              Save + quit
:q!              Quit without saving
:Explore         File browser
:ls              List open buffers
:bn / :bp        Next / prev buffer
:b <n>           Jump to buffer n
:bd              Close current buffer
:sp file.yaml    Open in horizontal split
:vsp file.yaml   Open in vertical split
Ctrl+w w         Cycle between splits
Ctrl+w h/j/k/l  Move to split ←↓↑→
Ctrl+w =         Equalize split sizes
Ctrl+w _         Maximize current split height
Ctrl+w |         Maximize current split width
Ctrl+w q         Close current split
```

### YAML Survival

```
:set paste       Paste without auto-indent hell
:set nopaste     Back to normal
:set number      Show line numbers
:set expandtab   Spaces instead of tabs
:set tabstop=2   2-space tabs
:set shiftwidth=2
:set ai          Auto-indent (match prev line)
:set hlsearch    Highlight all search matches
:noh             Clear search highlight
:set cursorline  Highlight current line (find yourself in deep YAML)
```

One-liner to set all at once:
```
:set paste number expandtab tabstop=2 shiftwidth=2 ai hlsearch cursorline
```

### YAML Editing Tricks

```
>>  / <<         Indent / unindent current line
5>>              Indent 5 lines
=G               Auto-indent from cursor to end of file
=i{              Auto-indent inside {} block
vi{              Select inside {} block
vat              Select entire XML/HTML tag (works for YAML maps too)
```

Folding (navigate big YAML):
```
:set foldmethod=indent
zc               Fold (close) current block
zo               Open fold
za               Toggle fold
zM               Fold everything
zR               Unfold everything
```

### Registers & Marks

```
"ayy             Yank line into register a
"ap              Paste from register a
:reg             Show all registers (see what you copied)
ma               Set mark a at cursor
'a               Jump to mark a
```

### Macros (repeat complex edits)

```
qa               Start recording macro into register a
(do your edits)
q                Stop recording
@a               Play macro a
5@a              Play macro a 5 times
```

Example: wrap every value in quotes across lines — record once, replay N times.

### Copy Blocks Fast

```
5yy              Copy 5 lines
5dd              Cut 5 lines
d$               Delete to end of line
dG               Delete to end of file
ciw              Delete word + enter insert (change inner word)
ci"              Change inside quotes
di(              Delete inside parens
```

## Tmux

### Sessions

```bash
tmux                          # New session
tmux new -s exam              # Named session
tmux ls                       # List sessions
tmux attach -t exam           # Reattach
```

### Prefix: Ctrl+b (then key)

### Panes (split screen)

```
Ctrl+b %         Split vertical
Ctrl+b "         Split horizontal
Ctrl+b ←↑↓→     Switch pane
Ctrl+b z         Zoom pane (toggle fullscreen)
Ctrl+b x         Kill pane
Ctrl+b {  / }    Swap pane left / right
```

### Windows (tabs)

```
Ctrl+b c         New window
Ctrl+b n / p     Next / prev window
Ctrl+b <n>       Go to window n
Ctrl+b ,         Rename window
Ctrl+b &         Kill window
```

### Scroll / Copy

```
Ctrl+b [         Enter scroll mode (then arrow/PgUp)
q                Exit scroll mode
```

## Exam Workflow

```bash
# Start tmux with two panes: editor left, kubectl right
tmux
Ctrl+b %
# Left pane: vim file.yaml
# Right pane: k apply -f file.yaml
# Ctrl+b ← / → to switch between them
# Ctrl+b z to fullscreen whichever you're in
```
