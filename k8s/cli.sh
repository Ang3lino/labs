# read, modify and switch from contexts
k config current-context
k config get-contexts
k config use-context $DESIRED_CONTEXT

# manual for k commands
k run -h | less

# Obtain a simple template with --dry-run=client arg (can be more simple still)
k run nginx --image=nginx --dry-run=client -o yaml >nginx.yaml

k create -f nginx.yaml
k apply -f nginx.yaml
k get pods
k describe pod nginx
