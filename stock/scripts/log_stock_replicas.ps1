$a = kubectl get pods --all-namespaces | Select-String 'stock'
$a | foreach-object {
$_.toString().Split(" ") | where {$_ -like "stock*"

}} | foreach-object { 
    echo $_  
    kubectl logs $_ 
    echo `0
    echo __________________________________________________________________________________________________________________________
    echo `0
}