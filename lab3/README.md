# Лаба 3 — k8s control-plane

## Часть 0: Сервисы

> Кто мы? Бэкендеры.
> 
> Будем ли мы генерировать код сервисов? Не будем.
> 
> А что будем делать? Самостоятельно напишем.

Мы запарились и написали ручками API-сервис и (не очень качественный, так как терпения не хватило) worker

Запуск всего великолепия (но сначала .env надо бы заполнить):

```docker compose up --build  ```

![alt text](screens/1.png)

## Часть 1: Выбор политик ограничений работы кластера

Для того, чтобы работа кластера была безопасной запросы отправляемые к k8s (принимаются API-сервером) проходят через 3 проверки:

   1. Аутентификация (проверка токена / логина и пароля)
   2. Авторизация (RBAC, проверка доступных действий для роли )
   3. Admissions (политики доступа) 
   
**Движок политик (policy engine)** - удобный механизм управвления политиками доступа, который интегрируется в работу k8s посредством перхвата запросов к API-серверу, и дальнейшем применением к ресурсам k8s.

В качестве policy engine был выбран Kyverno - простой и легкий в освоении за счёт работы через .yaml файлы.

В качестве движка k8s был выбран kind, но в качестве движка для контейнеров он использует orbstack. 

### Запуск k8s и всего что нужно в нём

1. Создадим кластер с именем k8s-lab3 и проверим его существование. Для этого напишем и примением cluster-config.yml

```
## cluster-config.yml

kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
  - role: worker

```

через команду

```kind create cluster --name k8s-lab3 --config k8s/cluster-config.yaml --verbosity 10 --wait 5s```

![alt text](screens/2.png)

>
> Маленькое время ождидания перехода ноды с control-plane привело к таймауту. В любом случае, кластер создался, но 5 секунд, запомним на будущее, кластеру для создания мало :D
>

![alt text](screens/3.png)

2. Теперь необходимо загрузить образы api и worker 
   
```
kind load docker-image api:v1 --name k8s-lab3

kind load docker-image worker:v1 --name k8s-lab3

```

![alt text](screens/4.png)

> В kind, по умолчанию, на control-plane ноде нет taint'а для ограничения запуска сторонних подов -- сделано это для того, чтобы локально поднимаемый кластер вообще запускался (ведь можно создать кластер с единственной нодой).

3. С помощью helm поставим в кластер Kyverno

```

helm repo add kyverno https://kyverno.github.io/kyverno/


helm repo update


helm install kyverno kyverno/kyverno -n kyverno --create-namespace


```

![alt text](screens/5.png)

>
> Мне тут же вылетел warning -- создалась одна реплика admission-controller'а, что однозначно является узким местом.
> 
>  Все из-за установленной по умолчанию политики failurePolicy: Fail ("если Kyverno не отвечает -- запрос отклоняется"). 
> 
> Единствкенный экземпляр admission-controller, в случае падения, перекроет все настроенные на проверку операции изменения ресурсов в кластере. 
>
> Поэтому ниже я решил обновить chart с добавлением еще двух реплик admission-controller Kyverno

Было:

![alt text](screens/6.png)

Стало: 

```
helm upgrade kyverno kyverno/kyverno -n kyverno --set admissionController.replicas=3

```
![alt text](screens/7.png)

![alt text](screens/8.png)


### Политики Kyverno


Выберем 5 политик, которые применим к кластеру
   
- **Require Limits and Requests** -- каждый из подов будет обязан иметь указанные requests (сколько необходимо для запуска ресурсов) и limits (максимум потребления для пода)

   >
   > Чтобы учесть политику и при этом не ограничать под cpu-лимитом выставим его просто достаточно большим
   >

- **Disallow Privileged Containers** -- запрет на создание подов с привелигированным доступом
- **Require Non-Root User** -- запрет запуска подов от root-пользователя
- **Require Probes** -- требует чтоб у всех подов были определены livenessProbe и readinessProbe 
- **Require Labels** -- требует наличия меток на подах

Напишем 5 yaml файлов с каждым из правил -- затем применим все правила.


>
> В текущей версии ClusterPolicy уже устаревшим называют... ну да ладно.
>

```

kubectl apply -f k8s/kyverno-polices/

kubectl get cpol

```

![alt text](screens/9.png)

Теперь подготовим "битые" манифесты

>
> На этом шаге успели добавить kyverno и системные поды в исключения, поменять режим проверки на политик с Audit на Enforce, добавить эндпоинт worker-у для того, чтобы livenessProbe прошел -- в общем, везде имеются свои подводные камни
>

![alt text](screens/10.png)

и применем по одному

![alt text](screens/11.png)

![alt text](screens/12.png)

![alt text](screens/13.png)

![alt text](screens/14.png)

![alt text](screens/15.png)

Kyverno успешно отклонил все неправильные поды

## Часть 2: Чарт api и worker

Создадим chart для нашего сервиса shop

```
...
shop-chart/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── api-deployment.yaml
    ├── api-service.yaml
    ├── worker-deployment.yaml
    └── worker-service.yaml

```

Добавим чарт с помощью helm

```
helm install shop ./k8s/shop-chart -n default

```
![alt text](screens/16.png)

>
> И тут случилось страншное -- все образы собрались как runAsNonRoot: False... -- пришлось снова ребилд делать, потом загружать и переприменять ресурсы
>

Теперь, чтобы полноценно протестировать, установим через helm БД в кластер

```

helm repo add cnpg https://cloudnative-pg.github.io/charts

helm repo update

helm install cnpg cnpg/cloudnative-pg -n cnpg-system --create-namespace

```

![alt text](screens/17.png)

Теперь добавим еще два шаблона в чарт -- postgres-cluster.yaml и postgres-secret.yaml, а затем снова сделаем helm upgrade

![alt text](screens/18.png)

Теперь попробуем удалить под с api, и убедимся, что Kubernetes сразу решит привести к spec-состоянию кластер

```
kubectl delete pod api-5df96b5987-2dl74

```

Можем убедиться, что под снова поднялся

![alt text](screens/19.png)

Теперь обновим число реплик в values.yaml (3 -> 6, 2 -> 4)

![alt text](screens/20.png)

Применим через helm изменения в чарте.

```
helm upgrade shop ./k8s/shop-chart -n default

```

Количетсво подов увеличилось!

![alt text](screens/21.png)

Теперь выполним эмуляцию rolling update. Для этого напишем Job'у, которая будет выполнять healthcheck, пока будет происходить update подов с новым тегом.

```
kubectl apply -f k8s/healthcheck-attack-job.yaml

```

Job заработала (healthcheck успешно отправляется), и теперь я могу поменять чарт.

![alt text](screens/22.png)

Поменяем версию api и внесем изменения в чарт.

![alt text](screens/23.png)


Все 6 подов успешно запустились вновь (хэш и время старта работы изменились, что свидетельствует об их новизне)

![alt text](screens/24.png)

Теперь переосберем образ с HEALTH_FAIL=True для демонстрации неудачного обнолвения, и, поменяв значение в values.yaml, обновим чарт.

Обновление кластера зависло

![alt text](screens/25.png)

Поды перезагружаются в надежде запустится

![alt text](screens/26.png)

При этом Job'а успешно отрабатывает

![alt text](screens/27.png)

Выполним откат версии

```

helm rollback shop

```
и убедимся что все поды снова живы


![alt text](screens/28.png)

## Часть 3: Postgres

Т.к. БД у нас уже развернута, попробуем убить один из подов, чтобы убедиться что он вернется

![alt text](screens/29.png)

```

kubectl delete pod postgres-1

```

![alt text](screens/30.png)

![alt text](screens/31.png)

![alt text](screens/32.png)

Проверим spec и status из .yaml

![alt text](screens/33.png)

![alt text](screens/34.png)

Оператор успешно справился с восстановлением реплики postgres.
Он отличается от controller-manager:
- Оператор -- контроллер, реализованный в виде отдельного пода и знающий специфику своей управляемой системы (для postgres -- о наличии primary-реплики, порядок восстанолвения из бэкапа и т.п.)
- controller-manager -- встроенный в Kubernetes компонент, относящийся к control-plane. Он не учитывает специфику пода, а просто реализовывают reconcliation-loop -- подгоняет действительное число подов к ожидаемому


## Часть 4: Падение control-plane

Запомним некоторые адреса подов -- нам понадобятся чтобы проверить их живость

![alt text](screens/35.png)

Выполним остановку etcd. Для этого зайдем через exec в контейнер control-plane и "избавимся" от его манифеста

```
docker exec k8s-lab3-control-plane mv /etc/kubernetes/manifests/etcd.yaml /tmp/

```

т.к. etcd остановлен, запрос не проходит

![alt text](screens/36.png)

Проверим, в обход kubectl, что поды живы

```
docker exec k8s-lab3-worker curl -s -o /dev/null -w "%{http_code}\n" http://10.244.3.23:8000/health

```

![alt text](screens/37.png)

И вернем обратно к жизни etcd, а также удостоверимся, что кластер снова отвечает на запросы

![alt text](screens/38.png)


## Часть 5. Мониторинг

>
> Prometheus'а нет... его поставить, добавить эндпоинты и снова load'ить образы в кластер...
>

Установим использованный ранее стек Prometheus, создав отедльный namespace для его подов

![alt text](screens/39.png)

![alt text](screens/40.png)

Обновим код api и worker, пересоберем их и загрузим в кластер

![alt text](screens/41.png)

Обновим values.yaml и чарт в кластере, а затем, с помощью проброса портоа, проверим ответ от api и worker'а

![alt text](screens/42.png)

![alt text](screens/43.png)

Напишем service-monitor для api и worker

![alt text](screens/44.png)

![alt text](screens/45.png)

Обновим чарт и проверим, что поды поднялись

![alt text](screens/46.png)

Пробросим порт и зайдем на localhost:9090 (UI Prometheus)

![alt text](screens/47.png)

![alt text](screens/48.png)

>
> а дальше полчаса поисков почему в /targets не появлялись api и worker... метку забыл в Service добавить -- а Prometheus хитрый, не нашел метку и молчит... -- стоило добавить требования к меткам еще и у Service... ну да ладно
>

В общем-то, все работает!

![alt text](screens/49.png)

Теперь напишем правила в шаблоне Prometheus:
- ApiDown -- если все поды с api упали, происходит алерт, уровень critical
- WorkerDown -- то же самое, но для воркера
- ApiManyRestarts -- warning при частой перезагрузке api

Обновим вновь чарт

![alt text](screens/50.png)

![alt text](screens/51.png)

Поменяем spec по api -- таким образом должен вызваться firing

```
kubectl scale deploy/api --replicas=0

```
Алерт пришел, потому что ни одного пода api больше не оказалось

![alt text](screens/52.png)


## Выводы

Kubernetes -- это великолепное ПО. Даже несмотря на то, что лаба делалсь 4 дня ("прошел афганскую войну" и все в этом духе), было очень интересно и познавательно!