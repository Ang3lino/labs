
alias k='kubectl'

source /etc/bash_completion
source <(kubectl completion bash)
complete -o default -F __start_kubectl k

alias kgp='kubectl get pods'

