# Web-scale Data Management Project

Extended project template with Python's Flask and Mongo. 

## 1. Final Presentation

You can find our final presentation [here](./Final_Presentation.pdf) or on google drive in the most updated format [here](https://docs.google.com/presentation/d/1B69Z2kFN7VWH64XOEWumz8aMrT2NyA9AVfZpilaWBok/edit?usp=sharing).

## 2. Project structure

* `env`
    Folder containing the env variables for redis and mongo for the docker-compose deployment
    
* `helm-config` 
   Helm chart values for mongo and ingress-nginx
        
* `k8s`
    Folder containing the kubernetes deployments, apps and services for the ingress, order, payment and stock services.
    
* `order`
    Folder containing the order application logic and dockerfile. 
    
* `payment`
    Folder containing the payment application logic and dockerfile. 

* `stock`
    Folder containing the stock application logic and dockerfile. 

* `test`
    Folder containing some basic correctness tests for the entire system. (Feel free to enhance them)



## 3. Deployment

This section describes the setup required and the process of deploying and running our project.

### 3.1. Requirements

Before you begin, make sure you have the following installed, and you are connected to the internet.

- kubectl [install guide](https://k8s-docs.netlify.app/en/docs/tasks/tools/install-minikube/)
- Helm [install guide](https://helm.sh/docs/intro/install/)
- Minikube [install guide](https://k8s-docs.netlify.app/en/docs/tasks/tools/install-minikube/)

### 3.2. TL;DR Startup Script

If you want to simply startup everything without much thinking run following script.

```
./super-start.sh
```

### 3.3. Manual Startup

In a case something does not work follow this guide for manual deployment. Please follow the steps as described below:

#### 3.3.1. Start Minikube

Start your minikube cluster.
```
minikube start
```

#### 3.3.2. Deploy Mongo database with Helm
Run our script to fetch Mongo recipe and deploy it 

``` 
./deploy-charts-minikube.sh
``` 

#### 3.3.3. Deploy Applications

Apply the defined scheme in `k8s` folder.

```
cd ./k8s
kubectl apply -f .
```


.

.

.

.

.

.


---

## 4. Old Deployment
The project template contained the following information for deployment and startup

### 4.1. docker-compose (local development)

After coding the REST endpoint logic run `docker-compose up --build` in the base folder to test if your logic is correct
(you can use the provided tests in the `\test` folder and change them as you wish). 

***Requirements:*** You need to have docker and docker-compose installed on your machine.

### 4.2. minikube (local k8s cluster)

This setup is for local k8s testing to see if your k8s config works before deploying to the cloud. 
First deploy your database using helm by running the `deploy-charts-minicube.sh` file (in this example the DB is Redis 
but you can find any database you want in https://artifacthub.io/ and adapt the script). Then adapt the k8s configuration files in the
`\k8s` folder to mach your system and then run `kubectl apply -f .` in the k8s folder. 

***Requirements:*** You need to have minikube (with ingress enabled) and helm installed on your machine.

### 4.3. kubernetes cluster (managed k8s cluster in the cloud)

Similarly to the `minikube` deployment but run the `deploy-charts-cluster.sh` in the helm step to also install an ingress to the cluster. 

***Requirements:*** You need to have access to kubectl of a k8s cluster.
