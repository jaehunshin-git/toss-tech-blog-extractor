# 대규모 CDC Pipeline 운영을 위한 Debezium 개선 여정

**Date:** 2024년 7월 18일
**URL:** https://toss.tech/article/cdc_pipeline

---

안녕하세요. 토스증권 실시간 데이터 팀 김용우 입니다.

Change Data Capture\(이하 CDC\)는 쉽게 말하면 정적인 데이터를 동적인 형태로 복제하는 것인데요. 데이터베이스 안에서 일어나는 변경사항들을 감지하고, 각 변경사항을 이벤트로 변환해서 이벤트 스트림으로 전송할 수 있게 해줘요. CDC의 장점은 데이터베이스의 변경사항을 실시간으로 받을 수 있다는 점입니다. 이런 데이터를 새로운 데이터베이스에 저장하거나, 새로운 기능을 만들거나, 데이터 후속처리할 때 사용할 수 있어요.

토스증권에서는 이미 다양한 데이터들에 대해 CDC 기술을 도입하고 있습니다. Data Analyst 분들이 사용하는 분석계 데이터, ML Engineer 분들이 학습용 데이터, 토스 앱에서 사용되는 서비스용 데이터 등 다양한 분야에서 CDC를 도입하여 실시간으로 데이터를 제공하고 있었습니다. 특히 CDC를 오픈소스로 제공하는 [Debezium](https://debezium.io/)을 적극 도입하여 사용 중에 있습니다. 문제 없이 여러 데이터들을 CDC를 통해 제공하던 어느 날, 근본적인 질문이 하나 떠오릅니다. 우리의 CDC는 얼마나 잘 운영되고 있는가? CDC가 잘 운영되고 있다는걸 우리는 어떻게 믿을 수 있을까? 

## CDC를 잘 운영한다는 것

CDC는 좋은 도구이지만 hourly 혹은 daily로 처리하던 배치\(Batch\) 처리하던 데이터들을 스트리밍\(Streaming\) 처리로 바꾼다는 건 늘 큰 부담이 됩니다. 배치 처리는 처리한 데이터의 처음과 끝을 알 수 있고 처리에 소요된 시간을 알 수 있는 반면, 스트리밍 처리를 하게 되면 특정 시간에 어떤 데이터가 처리되었는지, 처리되는데 소요된 시간 등을 정확하게 확인하기 어렵고 이는 곧 운영의 어려움으로 이어집니다. 

현재의 Debezium을 활용한 CDC에서는 이 질문에 답할 수 없었습니다. CDC Pipeline들에서 발생한 문제들을 짐작만 하고 있거나, 데이터 사용자들에게 문제를 보고 받았을 때야 문제를 인지할 수 있었습니다. Pipeline의 상태에 대한 무지로 인해 CDC를 더 많은 곳에 활용하기 꺼려지도록 만들었고, 새로운 pipeline이 늘어남에 따라 CDC 운영이 큰 짐이 되어갈 뿐이었습니다. 

그래서 저희는 CDC Pipeline을 잘 운영하기 위해, 여러 지표를 세우고 그 지표를 개선하기 위해 노력했어요. Connector의 개선, Debezium Source Code 수정, 운영 방식에 대한 변경을 통해 더 가시적인, 더 활용도 높은 CDC Pipeline 생애 주기를 만들고자 하였고, 오늘은 그 여정의 일부를 소개하고자 합니다. 많은 여정 중, 특히 CDC의 주된 사용 케이스인 원천 데이터베이스를 통해 만들어낸 Event를 다른 Target System에 저장하는 경우를 다뤄보겠습니다. 

## ‘잘 운영한다’의 기준

우선 지표를 세워야 합니다. CDC Pipeline이 잘 운영된다고 믿고 싶다면, 앞으로도 변화에도 잘 운영될 수 있다면 어떤 지표들을 세워야 할까요. 저희는 Target System에 데이터를 저장하는 CDC Pipeline의 운영을 위해서는 크게 4가지 핵심 지표를 선정했어요. 

  1. Source-to-Target Latency: 원천 데이터베이스에서 Target System으로 Event를 보내는데 걸리는 시간
  2. Events Per Second: 초당 처리할 수 있는 데이터의 양
  3. CDC Pipeline Scalability: 새로운 CDC 파이프라인을 만드는데 소요되는 시간
  4. Data Consistency: CDC Pipeline을 통해 만든 데이터의 정합성

오늘은 총 4가지 지표 중 운영과 관련이 된 1,2,3번 지표에 대해 저희의 개선사항들을 기술하고, 4번 정합성에 대한 이야기는 차후에 다뤄보도록 하겠습니다. 

## Source-to-Target Latency

우리의 궁극적인 목적은 원천 데이터베이스로부터 데이터의 변경사항을 실시간으로 추적하여, 변경사항을 Target System에 저장하는 것입니다. 그렇다면 당연하게도 가장 먼저 필요한 지표는 Source-to-Target Latency, 즉 ‘원천 데이터베이스에서 발생한 Event가 Target System에 얼마나 빨리 도착했는가’입니다. 원천 데이터베이스가 Target System에 도착하기 위한 세부 단계에서의 소요된 시간도 물론 확인하여야 하지만, 그보다 우선시 되어야 하는건 우리의 궁극적인 목적이 잘 수행되고 있는지 확인하는 것이죠. 

Source-to-Target Latency 지표를 기준으로 우리가 사용 중인 CDC Pipeline의 사용처를 결정할 수 있습니다. 지표를 기준으로 Tier을 아래와 같이 나눌 수 있어요.

  * Tier 1. 실시간 \(300ms\): 서비스용 데이터 System \(ex. 가원장 등\) 
  * Tier 2. Near Realtime \(10 seconds\): 서비스용 알람
  * Tier 3. 10 minutes: 지표와 관련된 서비스
  * Tier 4. 1 hour: 분석용 데이터

현재 pipeline은 여러 단계로 이루어져 있습니다. MySQL을 원천으로 사용하는 예시로 들면 MySQL로부터 Debezium MySQL Source Connector를 통해 Kafka Topic을 통해 데이터가 전달되고, Sink Connector는 Kafka로부터 정보를 받아 Event를 Sink Target에 저장합니다. 

Source Connector, Kafka Topic, Sink Connector 에서 각각 처리되는 Event들은 각각의 process에서 지표를 만들어 성능 측정을 하고 있습니다. 

  * Source Connector \(Debezium\) - [MilliSecondsBehindSource](https://debezium.io/documentation/reference/stable/connectors/mysql.html#connectors-strm-metric-millisecondsbehindsource_mysql)
  * Kafka - Consumer lag
  * Sink Connector \(kudu, clickhouse etc\)- Process time

하지만 우리는 전체적인 pipeline이 어떤 성능으로 처리되고 있는지 알지 못합니다. Source Connector와 Sink Connector에서 처리시간을 따로 기록하고 있지만 Kafka Topic에 consumer lag이 쌓이면 이 lag이 어느 정도 속도로 처리되었는지 가늠하기 어렵습니다. 또한 각 Source Connector에서 생성한 Event가 실제 Sink Connector에서는 언제 처리되었는지 추적하기 어려워요. Pipeline의 성능을 각각의 단계를 통해 가늠할 수 있을 뿐, 정확한 성능을 알 수 없습니다. 

따라서 pipeline의 정확한 성능 모니터링을 위해서는 end-to-end pipeline의 latency를 구할 필요가 있었고, 토스증권에서는 이 지표를 모니터링에 추가하고 추적하기로 했습니다. 

[Debeizum](https://debezium.io/documentation/reference/stable/connectors/mysql.html#mysql-monitoring)에서는 원천 데이터베이스에 event가 발생한 시간을 `source.ts_ms` 라는 필드로 제공합니다. 데이터베이스에서 실제 event가 발생한 시간이므로 event 생애 주기의 가장 처음이라 할 수 있겠죠. 우리는 이를 활용하기로 했습니다. Event의 생애 주기의 가장 마지막 단계인 Sink Connector에서 가장 첫 단계인 `source.ts_ms`를 비교합니다. Sink Connector에서 Target System에 데이터를 write한 처리시간 \(`sink process time`\)과 Source에서 데이터가 발생한 시간 \(`source.ts_ms`\)을 비교하고 이를 metric 지표로 나타낸다면 우리 pipeline의 현재 속도가 어떠한지 추적할 수 있습니다.

이를 통해 현재 pipeline의 지연도를 알 수 있고, 해당 지표들을 누적함에 따라 시간대별 성능을 알 수 있습니다. 저희는 이 지표를 각 CDC별 SLI로 잡고, 원하는 성능보다 좋지 않다면 개별 단계들의 지표를 확인하여 병목이 되는 지점을 확인했어요. 

## Events Per Second

Latency를 측정했다면 자연스레 throughput도 측정해야합니다. Pipeline이 어느 정도양의 데이터를 처리하고 있는지, 데이터 처리양 대비 latency는 어떻게 되는지 등을 확인하기 위함입니다. 

Sink Connector를 먼저 생각해보면 throughput은 간단하게 확인 가능합니다. Source Connector에서 제공된 CDC Event가 Kafka Topic으로 들어와있고, 해당 Topic이 Consume한 Event의 수를 확인하고, Target에 Write한 Event의 수를 기록해야 합니다. 

Source Connector는 경우가 다릅니다. 원천 Log\(`binlog`, `wal log`\)에 기록된 Event들은 물리 데이터베이스 전체에 대해 하나의 log에 기록되기 때문에 굉장히 많은 양의 데이터를 담고 있습니다. 이 중 실제로 CDC를 통해 확인하고 싶은 Table 혹은 데이터베이스들을 Event만 뽑아 CDC Event로 변환하여 Kafka Topic로 Produce합니다. 따라서 Throughput 확인을 위해서는 1\) 원천 Log에서 읽은 event의 양 2\) 이 중 Kafka Topic으로 Produce한 양 두 가지가 필요합니다. 

하지만 Debezium에서 제공하는 지표은 아래의 4가지입니다. 모두 1\) 원천 Log로부터 읽어들인 event의 양에 대한 지표만 제공하죠.

  * `TotalNumberOfEventSeen`
  * `TotalNumberOfCreateEventSeen`
  * `TotalNumberOfUpdateEventSeen`
  * `TotalNumberOfDeleteEventSeen`

따라서 우리는 기존에 Debezium에서 제공하는 metric들에 더해 실제로 변환된 CDC Event 수들, 기왕이면 Table별, Create, Update, Delete별로 Event를 분류하여 지표로 사용하고자 합니다. Create, Update, Delete 수를 통해 Table의 특성 \(예를 들면 Append Only인지 Update를 배치성으로 실행하는지 등\)도 쉽게 알 수 있고, Create와 Delete의 수를 통해 Target System에 반영되어야 할 데이터 정합성에도 활용할 수 있기 때문입니다. 

아래는 새로 추가한 throughput 지표입니다.

  * `TotalNumberOfEventSeenByTable`
  * `TotalNumberOfCreateEventSeenByTable`
  * `TotalNumberOfUpdateEventSeenByTable`
  * `TotalNumberOfDeleteEventSeenByTable`

    
    
    /**
     * Carries table-specific event metrics.
     */
    @ThreadSafe
    public class TableEventMeter {
    
        private final Map<String, AtomicLong> totalNumberOfEventsSeenByTable = new HashMap<>();
        private final Map<String, AtomicLong> totalNumberOfCreateEventsSeenByTable = new HashMap<>();
        private final Map<String, AtomicLong> totalNumberOfUpdateEventsSeenByTable = new HashMap<>();
        private final Map<String, AtomicLong> totalNumberOfDeleteEventsSeenByTable = new HashMap<>();
        private final Map<String, AtomicLong> numberOfEventsFilteredByTable = new HashMap<>();
        private final Map<String, AtomicLong> numberOfErroneousEventsByTable = new HashMap<>();
        private final Map<String, AtomicLong> lastEventTimestampByTable = new HashMap<>();
        private final Map<String, String> lastEventByTable = new HashMap<>();

## CDC Pipeline Scalability 

CDC Pipeline을 운영하다 보면 기존에 배치로 입수하던 데이터를 실시간으로 입수하길 원하는 니즈가 굉장히 많습니다. 데이터 입수를 배치 처리로 진행하게 되면 후속처리 단계에서 2-3배의 시간이 소요되기도 하고, 데이터 입수 속도가 빨라지는 것 만으로 가치가 높아지는 기능들도 많이 있으니깐요. 

하지만 테이블의 데이터양이 많을수록 초기 CDC Pipeline 생성에 오랜 시간이 소요됩니다. 최초의 CDC Pipeline 생성 시에는 Debezium에서 제공하는 [snapshot](https://debezium.io/documentation/reference/stable/connectors/mysql.html#mysql-snapshots)을 실행하게 됩니다. Snapshot 과정에서 Target Table의 모든 row들을 CDC Event로 변환하여 Kafka Topic으로 produce합니다. 이 과정은 single thread에서 처리되고 경우에 따라 11-12시간까지 소요되는 경우가 발생합니다. 초기 CDC Pipeline이 오래 걸린다는 뜻은 장애 상황 시 CDC Pipeline 복구에도 오랜 시간이 소요됨을 의미합니다. 데이터베이스의 오염, CDC Pipeline의 오염 등이 발생했을 때, 새로운 CDC Pipeline을 만들어야만 해결할 수 있는 상황이 종종 발생하고 이의 복구를 위해 최대 11-12시간이 걸린다는 뜻입니다. 

이를 개선하기 위해 토스증권에서 잘 활용하고 있던 도구인 [apache sqoop](https://sqoop.apache.org/)을 활용하였습니다. 최초의 CDC Pipeline 생성 시에 apache sqoop을 활용하여 현재 상태의 데이터를 Target System으로 적재하고, Debezium CDC에서 제공하는 `snpashot.mode : no_data` \([참고](https://debezium.io/documentation/reference/stable/connectors/mysql.html#:~:text=see%20no_data.-,no_data,-The%20connector%20captures)\)를 활용하여 원천 Log의 최초 시점부터 CDC를 적재하도록 하였습니다. 이를 통해 초기 CDC Pipeline의 생성을 스트리밍만 사용하던 환경에서 배치 + 스트리밍을 모두 활용하는 구조로 변경하여 생성시간을 단축하였습니다. 

두 번째로 이미 CDC를 활용하고 있던 데이터베이스에 새로운 Table을 CDC로 불러오고 싶은 경우입니다. 기존에는 Schema가 정해져 있었기 때문에 새로 추가가 안됐어요. 따라서 새로운 Table을 추가하고 싶을 때마다 새로운 CDC Pipeline이 필요해졌습니다. 이는 CDC Pipeline의 기하급수적인 증가를 야기하였고, 관리의 어려움으로 다가왔습니다. 또한 Source Connector 하나당 대상 데이터베이스의 Log를 읽어오는 커넥션이 하나씩 생성되기 때문에 너무 많은 Source Connector는 데이터베이스에 큰 부담을 주었습니다. 

이를 위해 Debezium에서 제공하는 `snapshot.mode`에 Table을 추가하는 mode를 개발 및 추가하여, Source Connector의 무분별한 신규 생성 없이 CDC Pipeline을 늘려나갈 수 있도록 개선하였습니다. 
    
    
    public class AddTableSchemaSnapshotter implements Snapshotter {
        private static final Logger LOGGER = LoggerFactory.getLogger(AddTableSchemaSnapshotter.class);
    
        @Override
        public String name() {
            return "add_table";
        }
    
        @Override
        public void configure(Map<String, ?> properties) {
    
        }
    
        @Override
        public boolean shouldSnapshotData(boolean offsetExists, boolean snapshotInProgress) {
            return false;
        }
    
        @Override
        public boolean shouldSnapshotSchema(boolean offsetExists, boolean snapshotInProgress) {
            return true;
        }
    
        @Override
        public boolean shouldStream() {
            return true;
        }
       ...

이 두 과정을 통해 CDC Pipeline의 추가 및 확장의 기대시간을 최대 12 시간에서 추가는 1시간, 확장은 5분 안으로 줄일 수 있었습니다. 

## 마치며

토스증권에서는 더 많은 실시간 CDC Pipeline을 만들고 관리하기 위한 준비를 마쳤습니다. 이제 CDC Pipeline이 어느 정도 성능인지 알 수 있고, 어느 속도와 양으로 데이터를 읽고 내보내고 있는지 알 수 있습니다. 새로운 Pipeline 추가가 계속해서 들어와도 문제 없이 대응할 수 있습니다. 다른 팀과 고객들에게 더 다양한 데이터를 빠르게 원하는 형태로 제공할 기반을 마련하였습니다. 

CDC는 데이터베이스의 데이터를 안정적으로 많은 분들께 전해드릴 수 있는 좋은 툴입니다. 성능에 대한 모니터링과 운영에 대한 이해가 생긴다면 더 많은 가치를 창출할 수 있다고 확신합니다. CDC를 도입하려는 많은 분들께 오늘 소개드린 저희의 준비과정들이 많은 도움이 될 수 있길 바랍니다. 

감사합니다. 

## Reference

Debezium - <https://debezium.io/>

CDC - <https://www.redhat.com/ko/topics/integration/what-is-change-data-capture>

kafka connect - <https://docs.confluent.io/platform/current/connect/index.html>