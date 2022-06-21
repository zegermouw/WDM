$a = kubectl get pods --all-namespaces | Select-String 'payment'
$a | foreach-object {
$_.toString().Split(" ") | where {$_ -like "payment*"

}} | foreach-object { 
    echo $_  
    kubectl logs $_ 
    echo `0
    echo __________________________________________________________________________________________________________________________
    echo `0
} 