#!/bin/bash
# history | cut -c 8- | sort | uniq | grep '^k' | nvim -

k
k apply -f namespace.yaml
k config current-context
k config set-context --current --namespace=mealie
k create deployment mealie --image=nginx --dry-run=client -o yaml >deploy.yaml
k create ns mealie --dry-run=client -o yaml >namespace.yaml
k delete ns mealie
k get ns
k get pods
kgp
kgp -n mealie
k ls
kpackagetool5
k run -h
k run misha-mealie --image=nginx -n mealie
ks
kubectl
kubectl config current-context
kubectl run -h
kubectl run -h | less
kubectl run -h | xclip
