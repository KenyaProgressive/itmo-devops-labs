# Лаба 4 — SLA критического пути под перегрузкой

>
> Сгенерировали код, который чисто создает процессы и жрет память. Вот прям жрёт
>

## Часть 1. Механизм разнесения

Тут нужно настроить распределение реплик между нодами для отказоустойчивости при выходе одной (нескольких) нод из строя.

Есть два варианта:
- `podAntiAffinity`, который позволяет запретить совместное размешение определенных подов на одной ноде
- `topologySpreadConstraints`, который позволяет равномерно размещать реплики между нодами

Мы выбрали второй вариант, так как в таком случае мы сможем равномерно распределить критически важный сервис между доступными нодами (а у нас их ограничено - будет их 2). У нас реплик api всего 6, поэтому мы получим 3 api на каждой ноде.

По настройкам. В [values.yaml](k8s/shop-chart/values.yaml) мы настраиваем:

```yaml
  placement:
    mode: topologySpreadConstraints     # режим
    topologyKey: kubernetes.io/hostname # ключ для распределения (по хостнейму ноды)
    maxSkew: 1  # допустимая разница в количестве реплик между нодами
```


И обновим шаблон [деплоймента апи](k8s/shop-chart/templates/api-deployment.yaml):
```yaml
spec:
    {{- if eq .Values.api.placement.mode "topologySpreadConstraints" }}
    topologySpreadConstraints:
      - maxSkew: {{ .Values.api.placement.maxSkew }}
        topologyKey: {{ .Values.api.placement.topologyKey | quote }}
        nodeTaintsPolicy: Honor # учет taint (для control plane)
        whenUnsatisfiable: DoNotSchedule # строгое правило для равномерного распределения, иначе pending
        labelSelector:
          matchLabels:
            app: api

    {{- else if eq .Values.api.placement.mode "podAntiAffinity" }}
    affinity:
      podAntiAffinity:
        preferredDuringSchedulingIgnoredDuringExecution: # не строгое правило при запуске пода (не трогать запущенные)
          - labelSelector:
              matchLabels:
                app: api
            topologyKey: {{ .Values.api.placement.topologyKey | quote }}
    {{- end }}
```

В `podAntiAffinity` используется не строгое правило `preferredDuringSchedulingIgnoredDuringExecution`. При нем кубер будет пытаться разнести реплики на разных нодах. Если вдруг где-то ресурсов например не хватит, то разместит на одной. В целом это повысит доступность api, в сравнении с `requiredDuringSchedulingIgnoredDuringExecution`

Проверка шаблона:

![template](img/template.png)

---

## Часть 2. Тесная площадка

Меняем наш кластер [конфиг](k8s/cluster-config.yaml) на 2 воркер ноды + control plane (не размещаем тут поды, запрещаем):

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          taints:
            - key: c-plane
              value: reserved
              effect: NoSchedule

  - role: worker
  - role: worker
```

Создаем кластер:

![cluster](img/startup.png)

Загружаем образы:

```bash
➜  lab4 git:(feat/lr4) ✗ kind load docker-image api:v4 worker:v2 --name lab4
Image: "api:v4" with ID "sha256:e4669f7d092b51eb17f81eb9b2033fd93b959f6115cf763064ec9c68747eb9f1" not yet present on node "lab4-worker2", loading...
Image: "api:v4" with ID "sha256:e4669f7d092b51eb17f81eb9b2033fd93b959f6115cf763064ec9c68747eb9f1" not yet present on node "lab4-worker", loading...
Image: "api:v4" with ID "sha256:e4669f7d092b51eb17f81eb9b2033fd93b959f6115cf763064ec9c68747eb9f1" not yet present on node "lab4-control-plane", loading...
Image: "worker:v2" with ID "sha256:7eec0f49b59d81f352bcb22ec161382610e08d12bba8437b135010259729d3f2" not yet present on node "lab4-worker2", loading...
Image: "worker:v2" with ID "sha256:7eec0f49b59d81f352bcb22ec161382610e08d12bba8437b135010259729d3f2" not yet present on node "lab4-worker", loading...
Image: "worker:v2" with ID "sha256:7eec0f49b59d81f352bcb22ec161382610e08d12bba8437b135010259729d3f2" not yet present on node "lab4-control-plane", loading...
➜  lab4 git:(feat/lr4) ✗ kind load docker-image batch:v1 --name lab4
Image: "batch:v1" with ID "sha256:6058d4cb74f0de467e8fd9f271f1d406390ccac0c9bb437f935e2fa9e61628be" not yet present on node "lab4-worker2", loading...
Image: "batch:v1" with ID "sha256:6058d4cb74f0de467e8fd9f271f1d406390ccac0c9bb437f935e2fa9e61628be" not yet present on node "lab4-worker", loading...
Image: "batch:v1" with ID "sha256:6058d4cb74f0de467e8fd9f271f1d406390ccac0c9bb437f935e2fa9e61628be" not yet present on node "lab4-control-plane", loading...
```

Так как у нас кластер новый, то установили инфру из предыдущих лаб (CloudNativePG, kube-prometheus-stack, Kyverno). А после установки киверно повторно применили политики из ЛР3:

```bash
➜  lab4 git:(feat/lr4) ✗ kubectl apply -f k8s/kyverno-polices/
Warning: kyverno.io/v1 ClusterPolicy is deprecated and will be removed in a future release; migrate to ValidatingPolicy, MutatingPolicy, GeneratingPolicy or ImageValidatingPolicy (policies.kyverno.io), see https://kyverno.io/docs/guides/migration-to-cel/
clusterpolicy.kyverno.io/disallow-privileged created
clusterpolicy.kyverno.io/req-labels created
clusterpolicy.kyverno.io/req-limits-requests created
clusterpolicy.kyverno.io/req-probs created
clusterpolicy.kyverno.io/req-user-no-root created
```

Добавим batch новым шаблоном в чарт shop [тык](k8s/shop-chart/templates/batch-deployment.yaml). И его конфигурацию в values:

```yaml
batch:
  replicas: 1
  image: batch:v1
  port: 8082

  resources:
    requests:   # это мы дальше по лабе исправим (лимиты цпу уберем, и реквесты с лимитами памяти сравняем)
      cpu: "100m"
      memory: "128Mi"
    limits:
      cpu: "500m"
      memory: "512Mi"

  config:
    memMb: 256
    cpuWorkers: 1
    growStepMb: 16
    growIntervalS: 2
    logIntervalS: 5
```


И устанавливаем наш shop-chart:

```bash
➜  lab4 git:(feat/lr4) ✗ helm install shop ./k8s/shop-chart -n default
NAME: shop
LAST DEPLOYED: Mon Oct 12 00:20:13 2026
NAMESPACE: default
STATUS: deployed
REVISION: 1
TEST SUITE: None
➜  lab4 git:(feat/lr4) ✗ helm list -n default
NAME    NAMESPACE       REVISION        UPDATED                                 STATUS          CHART           APP VERSION
shop    default         1               2026-10-12 00:20:13.961561271 +0300 MSK deployed        shop-1.0.0      1.0        
➜  lab4 git:(feat/lr4) ✗ 
```

Смотрим распределение наших реплик апи по нодам:

```bash
➜  lab4 git:(feat/lr4) ✗ kubectl get pods -l app=api -o wide
NAME                   READY   STATUS    RESTARTS   AGE   IP            NODE           NOMINATED NODE   READINESS GATES
api-8545dfd96f-6n99x   1/1     Running   0          50s   10.244.2.36   lab4-worker    <none>           <none>
api-8545dfd96f-8mqm2   1/1     Running   0          62s   10.244.1.26   lab4-worker2   <none>           <none>
api-8545dfd96f-bb8hl   1/1     Running   0          62s   10.244.2.34   lab4-worker    <none>           <none>
api-8545dfd96f-sss2q   1/1     Running   0          51s   10.244.1.29   lab4-worker2   <none>           <none>
api-8545dfd96f-x4pqn   1/1     Running   0          62s   10.244.1.27   lab4-worker2   <none>           <none>
api-8545dfd96f-xh46q   1/1     Running   0          51s   10.244.2.35   lab4-worker    <none>           <none>
➜  lab4 git:(feat/lr4) ✗ 
```

Видим, что реплики распределились 3 на 3 на двух нодах. Наш `batch` тоже работает:

```bash
➜  lab4 git:(feat/lr4) ✗ kubectl logs deployment/batch --tail=20
[batch-74bcd7b979-zstcj] mem=256MB steady cpu_workers=1
[batch-74bcd7b979-zstcj] mem=256MB steady cpu_workers=1
[batch-74bcd7b979-zstcj] mem=256MB steady cpu_workers=1
[batch-74bcd7b979-zstcj] mem=256MB steady cpu_workers=1
...
```