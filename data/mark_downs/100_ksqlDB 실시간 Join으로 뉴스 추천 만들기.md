# ksqlDB 실시간 Join으로 뉴스 추천 만들기

**Date:** 2024년 9월 23일
**URL:** https://toss.tech/article/ksqldb-realtime-data-2

---

안녕하세요. 토스증권 실시간 데이터 팀 리더 강병수입니다. 

[이전 아티클](https://toss.tech/article/ksqldb-realtime-data)에서는 토스증권의 ksqlDB 활용사례를 소개했는데요. 오늘은 ksqlDB의 강력한 Join 기능을 활용해서 토스증권의 다양한 로그를 실시간으로 조합하여 중요한 비즈니스 문제를 해결한 사례를 소개하려고 합니다. 

### MAB를 이용한 실시간 뉴스 추천

토스증권은 [MAB\(Multi-Armed Bandits\) 알고리즘](https://ko.wikipedia.org/wiki/%EB%A9%80%ED%8B%B0_%EC%95%94%EB%93%9C_%EB%B0%B4%EB%94%A7)을 이용해서 수많은 국내/해외 뉴스 중 유저가 흥미를 느낄만한 아티클을 찾고 제공하고 있습니다. 이 글은 ML이나 추천 과정을 자세히 기술하는 글은 아닙니다. 뉴스 추천이라는 멋진 요리를 만들기 위해서는 신선한 재료가 중요한데요. 신선한 재료를 어떻게 제공하는지에 관한 이야기입니다. 

정확하고 최신성을 유지하는 뉴스 추천 MAB 알고리즘을 위해서는 실시간으로 발생하는 유저의 뉴스 탭 방문과 뉴스 클릭 로그가 필요한데요. 유저의 실시간 뉴스탭 활동 로그를 score 갱신하는 피드백으로 사용하고 있기 때문이에요. Score를 계속 갱신해서 유저들이 흥미를 갖는 뉴스를 더 많이 노출하거나, 기존에 노출되는 뉴스보다 더 재밌는 뉴스를 찾습니다. 이 시스템의 핵심 재료는 ‘실시간으로 발생하는 뉴스탭 활동 로그’입니다.

MAB의 score 계산에는 CTR\(Click-Through-Rate\)을 핵심으로 사용하는데요. CTR을 계산하기 위해 두 가지 로그가 필요합니다. 뉴스 탭 impression 로그와, 뉴스 click 로그인데요. 실시간으로 발생하는 뉴스탭 활동 로그에서 ksqlDB를 이용해 CTR 계산에 필요한 로그만 필터링해서 제공하면 이제 MAB 뉴스 추천을 만들 수 있게 됩니다.

이를 생성하는 ksqlDB 쿼리 \(이하 KSQL\)을 살펴보면 아래와 같이 간단하게 만들 수 있습니다.
    
    
    CREATE STREAM headline_news
    WITH (kafka_topic = 'headline_news',partitions = 3,replicas = 3) AS
    SELECT uid                                AS `uid`,
           CASE
               WHEN log_type = 'event' THEN 'click'
               WHEN log_type = 'impression' THEN 'impression'
           END                                AS `log_type`,
           section                            AS `section`,
           extractjsonfield(params, '$.news') AS `news`
    FROM s_client_log
    WHERE log_type IN ('impression', 'event') 
    			 AND url_encoder(section) = url_encoder('주요 뉴스')
    EMIT CHANGES;

신선한 재료를 실시간으로 제공한 결과 MAB를 이용한 추천을 통해 아래 사진과 같이 유저가 흥미를 느낄 만한 뉴스를 찾아서 제공하게 됩니다. 

### MAB에 개인화를 더하다

하지만 MAB 뉴스 추천은 여기서 끝이 아닙니다. 토스증권 ML 엔지니어 분들이 추천 알고리즘 성능을 개선하기 위해서 비슷한 성향을 가진 유저들을 구분하는 유저 클러스터링 모델을 만들었습니다. 이 유저 클러스터링 모델을 MAB 추천에 적용한다면 뉴스 클릭률을 더 높이는 것을 실험을 통해 밝혀냈고, 유저 클러스터링 결과를 MAB 추천에 적용하기로 했습니다.

ksqlDB이 해야 할 일은 이제 한 가지 더 늘어났습니다. 위에서 뽑아낸 뉴스 탭 impression 로그, 뉴스 click 로그에 각각 유저가 속한 클러스터 번호를 붙여주는 일입니다. 같은 클러스터 번호를 가진 유저들이 흥미를 갖는 뉴스 추천을 받게 되면서 더 재밌고 클릭률이 높은 뉴스탭으로 발전하게 됩니다.

토스증권의 유저 클러스터링 결과는 매일 갱신돼서 MongoDB에 저장됩니다. 실시간으로 발생되는 뉴스탭 활동 로그에 MongoDB에 있는 클러스터 번호를 꺼내서 붙여주려면 어떻게 해야 할까요? 이때부터 실시간 Join에 대한 니즈가 시작됩니다.

### 해결방안 \#1

먼저 가장 간단하게 구현해볼 수 있는 것은 뉴스탭 활동로그를 실시간으로 소비한 다음에 데이터베이스에 질의하여 해당 유저의 클러스터 번호를 가져와 붙여줄 수 있습니다. 이 방법은 구현은 간단하지만 다음과 같은 두 가지 문제를 동반합니다.

  1. ksqlDB를 사용하는 이유는 노코드 툴이라는 강점 때문인데, 외부 데이터베이스를 찔러서 값을 가져오는 로직 구현이 필요해졌습니다.
  2. 로그의 발생량은 굉장히 많습니다. 많을 때는 초당 5만건 이상 발생하고 있는데, 매 로그마다 데이터베이스에 질의를 한다면 데이터베이스는 초당 5만건의 read 요청을 받아내야 합니다. 서비스 데이터베이스에 요청량이 과도하게 많아질 경우 위험성이 증가할 수 있습니다.

### 해결방안 \#2

ksqlDB의 Table, Stream Join을 이용해 이러한 비즈니스 요건을 멋지게 해결해내는 방법입니다. 

Kafka Topic을 Stream과 Table 형태로 변환하면 ksqlDB에서도 활용할 수 있어요. ksqlDB에서 Stream 형태를 KStream이라고 하고, Table 형태를 KTable이라고 부릅니다. 자세한 차이점은 [공식 문서](https://www.confluent.io/blog/kafka-streams-tables-part-1-event-streaming/)에서 확인할 수 있어요.

MongoDB의 유저 클러스터링 결과를 담고 있는 컬렉션\(이하 테이블\)을 KTable로 만들고, 뉴스탭 활동 로그를 KStream으로 만들어서 이 둘을 Join 연산을 통해 실시간으로 완성된 데이터를 만들어내는 식입니다.

먼저 실시간 Join KSQL을 살펴보면 아래와 같습니다. 
    
    
    CREATE STREAM headline_news_mab_with_cluster_id  
    WITH (kafka_topic='headline_news_mab_with_cluster_id',value_format='JSON',partitions = 3) AS
    SELECT A.`id`,
           A.`uid`      AS `uid`,
           A.`log_type` AS `log_type`,
           A.`section`  AS `section`,
           A.`news`     AS `news`,
           CASE
               WHEN B.`cluster_id` IS NULL THEN -1
               WHEN B.`is_deleted` = true THEN -2
               WHEN B.`is_deleted` = false THEN B.`cluster_id`
           END          AS `cluster_id`
    FROM headline_news_mab_kstream A
             LEFT JOIN mongodb_user_cluster_ktable B
                       ON A.`id` = B.`id` 
    EMIT CHANGES;

ksqlDB의 Join은 Stream-Stream, Stream-Table, Table-Table [세 가지 방식](https://docs.ksqldb.io/en/latest/developer-guide/joins/join-streams-and-tables/#join-capabilities)을 지원하는데요. 토스증권에서 필요한 비즈니스 요건들은 Stream-Table Join으로 해결 가능한 것이 많아서 대부분 Stream-Table Join을 활용하고 있습니다.

`headline_news_mab_kstream` 이라는 KStream을 `mongodb_user_cluster_ktable` KTable을 `LEFT JOIN` 하고 있고, Join `key`는 `id`라는 공통된 값을 가진 필드를 쓰고 있습니다.

  * `LEFT JOIN`을 하는 이유는 뉴스탭 활동 로그 KStream은 유저 클러스터링 KTable에 같은 `id`가 없더라도 유실되면 안 되기 때문에 `INNER JOIN`이 아닌 `LEFT JOIN`을 사용했습니다.

위 쿼리의 수행 결과로 `headline_news_mab_with_cluster_id` Kafka 토픽에 아래와 형태로 메시지가 들어오게 됩니다.
    
    
    {
    	"uid": "******",
    	"log_type": "impression",
    	"section": "개인화뉴스",
    	"news": ["y_usa_1","a_2","e_3","f_4"],
    	"cluster_id": 57 -- 본인이 속한 클러스터 번호가 추가됨
    }

굉장히 간단하게 실시간으로 Join 연산을 수행해주는 프로그램 개발을 해냈습니다. 

결과물을 먼저 봤으니, 

  1. KStream과 KTable을 어떻게 만들었는지
  2. Join이 정확하게 동작하기 위한 작업들

에 대해 하나씩 설명드릴게요.

### KStream과 KTable 만들기

먼저 KStream을 만드는 방법입니다. Kafka 토픽을 ksqlDB에서 사용할 수 있는 형태로 스트림화 합니다.
    
    
    CREATE STREAM s_headline_news (
    	uid VARCHAR,
    	log_type VARCHAR,
    	section VARCHAR,
    	news VARCHAR
    )
    WITH (kafka_topic='headline_news',value_format='json',
        partitions=3);
    
    

위와 같은 형태의 KSQL은 ksqlDB에 Kafka 토픽에 대한 정보와 스키마를 알려주는 작업입니다. 이처럼 메타정보를 ksqlDB에 등록해줘야 ksqlDB에서 Kafka Topic을 활용할 수 있게 됩니다. 메타 정보를 입력하는 과정이기 때문에 실제 메시지 소비가 발생하지 않습니다. 

Kafka Topic의 메시지가 [Confluent Schema Registry](https://docs.confluent.io/platform/current/schema-registry/index.html)에 스키마로 등록돼 있는 경우에는 메시지 포맷에 대한 스키마 정의가 필요 없지만, 스키마가 등록돼 있지 않은 JSON 포맷 토픽의 경우 ksqlDB가 스키마를 알 수 없기 때문에 정확한 스키마를 정의해 줘야 합니다.

실제 메시지 소비가 시작되는 Stream 생성 KSQL은 아래와 같습니다.
    
    
    CREATE STREAM headline_news_mab_kstream
    WITH (kafka_topic='headline_news_mab', value_format = 'json', partitions = 3) AS
    SELECT toss_coalesce_with_default('null', uid) AS `id`,
           as_value(uid)                           AS `uid`,
           log_type                                AS `log_type`,
           section                                 AS `section`,
           news                                    AS `news`
    FROM s_headline_news 
    PARTITION BY toss_coalesce_with_default('null', uid) 
    EMIT CHANGES;
    
    

위 쿼리에서 명시한 동작과 스키마 대로 실시간으로 원천 Kafka Topic의 메시지를 변환하여 `headline_news_mab` 라는 Kafka Topic으로 메시지를 생성합니다. `PARTITION BY` 라는 문법이 보이는데, Join이 정확하게 동작하기 위해 필요합니다. 아랫부분에서 더 자세하게 설명드릴게요.

`headline_news_mab` 토픽에 생성된 결과물인데, KStream만 존재할 때는 Join 결과물에서 추가해준 `cluster_id` 정보가 없는 것을 확인할 수 있습니다.
    
    
    {
    	"uid": "******",
    	"log_type": "impression",
    	"section": "개인화뉴스",
    	"news": ["h_1","e_2","y_usa_3"]
    }

다음은 KTable을 만드는 방법입니다. 

ksqlDB는 Kafka Topic을 컨슘해서 KStream과 KTable을 만들기 때문에 KTable을 만들 때 사용할 원천 데이터가 Kafka Topic에 적재돼 있어야 합니다. 그러므로 MongoDB 테이블의 전체 스냅샷과 이후 실시간 변경사항을 Kafka Topic에 넣어줘야 합니다.

이런 역할을 잘 해주는 것이 CDC\(Change Data Capture\) 인데요. 저희는 debezium 오픈소스를 활용해서 MongoDB CDC를 수행하고 있습니다. CDC에 대한 자세한 설명은 토스증권 실시간 데이터 팀 김용우님이 작성한 [대규모 CDC Pipeline 운영을 위한 Debezium 개선 여정](https://toss.tech/article/cdc_pipeline) 아티클에서 더 자세히 볼 수 있습니다. 

CDC 과정을 통해 테이블이 스트림화 되어 Kafka Topic으로 잘 들어온다면 이제 KTable을 만들 수 있습니다.

KStream을 만들었던 과정과 유사하게 스키마를 먼저 정의해줍니다.
    
    
    CREATE STREAM s_mongodb_user_cluster 
    WITH (kafka_topic='mongodb-user-cluster',value_format='AVRO');

토스증권은 현재 CDC 결과를 AVRO 포맷으로 내보내기 때문에 Kafka Topic의 메시지가 AVRO 포맷입니다. AVRO 포맷은 KStream에서 스키마를 정의해줬던 부분과 다르게 Confluent Schema Registry에 스키마가 존재하기 때문에 스키마 정의를 따로 하지 않는 것을 볼 수 있습니다.

스키마를 정의했으니 실제로 Kafka Topic의 메시지를 소비해서 KTable을 만드는 KSQL을 실행합니다.
    
    
    CREATE TABLE mongodb_user_cluster_ktable 
    WITH (kafka_topic = 'mongodb_user_cluster_ktable',value_format = 'JSON',partitions = 3,replicas = 3) AS
    SELECT uid                            AS `id`,
           as_value(uid)                  AS `uid`,
           latest_by_offset(cluster_id)   AS `cluster_id`,
           latest_by_offset(cluster_name) AS `cluster_name`,
           latest_by_offset(__deleted)    AS `is_deleted`
    FROM s_mongodb_user_cluster
    WHERE uid IS NOT NULL
    GROUP BY uid 
    EMIT CHANGES;

KTable 생성을 위해서는 primary key\(pk\)가 될 필드를 `GROUP BY` 문에 넣어줘야 합니다. 이미 존재하는 pk에 새로운 value가 들어오면 `LATEST_BY_OFFSET` 함수에 의해서 가장 최신 값을 사용합니다. pk가 `NULL`인 경우 에러가 발생하기 때문에 `WHERE uid IS NOT NULL` 을 이용해 `NULL`을 제거합니다.

위 KSQL을 요약해서 설명하면 pk인 `uid` key 별로 가장 최신 value를 유지하는 테이블이며, Key-Value 데이터베이스와 유사한 형태가 됩니다.

쿼리에 대한 설명이 아닌 KTable에 대한 추가적인 설명을 적어보면,

  * KTable은 동일한 key에 대한 결과 값을 영구 저장합니다.
  * 데이터는 빠른 성능을 위해 로컬 RocksDB에 저장해서 활용하고, 영구 저장을 위해 Kafka compact Topic에 동시 저장 함으로써 어떤 상황에도 로컬 RocksDB로 다시 복구할 수 있도록 백업합니다.
  * KTable은 원천 데이터베이스 테이블을 사용하는 것이 아닌 Kafka Topic에 스트림화 된 메시지를 소비해서 자체적인 테이블로 만들어 저장하기 때문에 원천 데이터베이스 테이블과 물리적으로 분리됩니다.
  * 이는 원천 데이터베이스와 물리적으로 분리됐지만 실시간으로 상태 동기화가 되고 있는 Materialized View와 같이 동작합니다.
  * 물리적으로 분리된 테이블을 이용해 Join 연산을 수행하기 때문에, 해결방안 \#1 에서 문제가 됐던 서비스 데이터베이스에 조회 쿼리를 발생시켜 위험을 높이는 현상이 발생하지 않습니다.
  * 이는 서비스 데이터베이스 Read 분산 효과를 주기 때문에 우수한 아키텍처라고 생각합니다.

### Join이 정확하게 동작하기 위해 알아야 하는 세 가지

Kafka Topic의 파티션 개수가 늘어날수록 대부분의 경우 선형적으로 성능이 좋아집니다. 따라서 적절한 수의 파티션 수를 설정하는 것이 유리합니다.

ksqlDB의 Join은 Kafka의 파티셔닝 정책을 적극적으로 활용합니다. Kafka의 파티션은 Kafka Topic을 적절한 크기로 샤딩해서 나눈 것이라고 생각해도 좋을 것 같습니다. 

Kafka Topic A와 Kafka Topic B를 KStream 또는 KTable로 만들어서 Join을 한다고 가정하면, Join을 위해 같은 값을 가진 Join key를 Kafka Topic 모든 파티션에서 찾는 것이 아닌 같은 파티션 번호끼리만 비교를 해서 찾습니다.

좀 더 상세하게 예시를 들어볼게요. A, B Kafka Topic 모두 \[ 0,1,2 \] 3개 파티션으로 구성돼 있을 때 A Topic의 0번 파티션에 들어온 메시지는 B Topic의 0번 파티션에서만 같은 값을 가진 key를 검색하고 없으면 Join 실패로 처리합니다.

이러한 구조 때문에 ksqlDB에서 정확한 Join 결과를 얻기 위해서는 세 가지를 신경써야 합니다.

  1. 각 Kafka Topic에 발생하는 메시지의 양을 고려해서 적절한 파티션 수를 설정해야 지연시간이 최소화되고 실시간 성격이 유지된다.
  2. Join하려는 대상은 파티션 숫자가 같아야한다.
  3. Join하려는 대상은 모두 같은 key를 이용해서 파티셔닝을 해야 한다. 

### \#1 적절한 파티션 수를 설정해야 한다 

파티션 숫자가 어느 정도가 적절한지에 대한 고민보다 런타임에 실시간 처리가 밀리지 않는 것이 서비스에서 가장 중요합니다. 

실시간으로 발생하는 메시지 양을 고려해서 밀리지 않을 적절한 파티션 수를 찾아야 합니다.

또 데이터베이스 테이블을 KTable로 만들어서 사용하는 경우 원천 테이블의 크기도 중요합니다. 

만약 원천 테이블이 10억건이 넘는 데이터를 갖고 있는 큰 테이블이라고 하면 파티션 1개로 만들어서 Join 할 경우 두 가지 문제가 생깁니다.

  1. 여러 파티션으로 샤딩돼 있는 것에 비해 Join key를 찾기 위해 더 많은 시간이 필요합니다.
  2. 데이터 저장 차원에서도 파티션 단위로 로컬 RocksDB에 저장하는 ksqlDB의 특성상 Disk 사용률에 skew가 발생합니다. 

각각 Kafka Topic 관점에서도 파티션 숫자는 중요하지만, ksqlDB의 연산 성능 관점에서도 파티션 숫자는 중요합니다. 파티션의 숫자만큼 병렬처리를 하기 때문에 파티션이 너무 작아서 실시간 처리가 지연이 발생한다면 파티션 숫자를 늘려서 해결하는 경우도 있습니다.

결국 실시간 발생하는 메시지 양과 원천 테이블의 크기 그리고 ksqlDB가 연산해야 하는 양을 고려하여 적절한 파티션 숫자를 선택하는 것이 중요합니다.

### \#2 파티션 숫자가 같아야 한다

파티션 숫자가 같아야 한다는 제약 때문에, Join 대상 테이블들 중 가장 메시지 발생이 큰 Kafka Topic의 파티션 숫자를 따라가야 합니다. 

이 때문에 발생하는 경우로 메시지 발생이 거의 없는 Kafka Topic임에도 어쩔 수 없이 10개가 넘는 파티션으로 생성하는 경우도 있습니다.

### \#3 파티셔닝 key가 같아야 한다

Kafka Topic의 기본적인 파티셔닝 룰은 같은 값을 가진 key는 언제나 같은 파티션으로 분배되는 것을 보장합니다. key를 해싱하고 파티션 수로 모듈러 연산을 하기 때문입니다. 
    
    
    10개 파티션을 가진 Kafka Topic의 파티션 결정 알고리즘
    hash(stock_code) % numTopicPartitions
    
    '토스증권'이라는 stock_code는 언제나 같은 파티션 번호로 가는 것이 보장된다.
    hash('토스증권') % 10 == 7

Join하려는 대상들은 언제나 같은 파티션 번호끼리 Join 연산을 수행합니다. Join 대상의 Kafka Topic들이 모두 같은 Join key로 파티셔닝을 해야 같은 파티션 번호에 같은 데이터가 존재하게 됩니다. 같은 key로 파티셔닝 하는 것이 보장돼야 ksqlDB의 Join이 누락 없이 정상적으로 수행됩니다. 

하지만 Kafka Topic에 메시지를 생성하는 주체는 여러 곳이기 때문에 같은 파티셔닝 key를 사용하고 있지 않은 경우가 많습니다. 

ksqlDB에서는 서로 다르게 파티셔닝 돼있는 경우에도 같은 파티셔닝 key를 이용해 새로 파티셔닝을 해주는 방법을 제공합니다. KStream 생성 예시에서 봤던 `PARTITION BY` key 가 그것인데요. 입력한 key 필드를 이용해서 파티셔닝을 해서 output Kafka Topic으로 새로 발행합니다.

KTable에서는 `GROUP BY` key 를 하게 되면 이 역시 key로 사용된 필드로 새로 파티셔닝 돼 output Kafka Topic으로 내보내게 됩니다.

이번 글의 사례에서는 KStream은 `PARTITION BY`를 이용해서, KTable은 `GROUP BY`를 이용해서 서로 파티션 분배 정책을 동일하게 맞춰준 것을 볼 수 있습니다. 이처럼 파티션 분배를 동일하게 하고 이후에 Join연산을 해야 정확한 결과를 얻을 수 있습니다.

Kafka의 파티션에 대한 이해와 위에서 설명한 세 가지 고려 사항을 잡 생성 전에 잘 설계해야 무사히 라이브 서비스를 내보낼 수 있는 실시간 Join 애플리케이션을 완성할 수 있습니다. Join에 대한 이해까지 모두 마쳤다면 조금만 응용한다면 ksqlDB를 이용해 요리에 필요한 신선한 재료들을 빠르고 정확하게 공급할 수 있게 됩니다. 

### 마무리

이번 글에서는 ksqlDB의 Join 기능을 이용해 여러 데이터 소스를 조합해서 완성된 결과물을 실시간으로 만드는 것을 소개 드렸습니다.

토스증권에서 실제로 활용 중인 사례를 통해 파이프라인을 만드는 전체적인 과정을 상세하게 공유드렸는데 개발 리소스가 전혀 들어가지 않고 간단한 절차 몇 가지로 라이브 서비스에 나가는 파이프라인을 완성한 것을 볼 수 있었습니다. 

이처럼 ksqlDB의 최대 장점은 ‘생산성’인데요. 생산성이 좋아지다 보니 문제를 풀기 위한 방법에 시간을 쓰는 것이 아닌 문제의 원인이 되는 비즈니스 요건에 더 집중하고 고민할 여유가 생겼습니다. 

토스증권 실시간 데이터 팀에서는 ksqlDB의 생산성을 적극적으로 활용해서 수많은 문제들을 빠르게 풀어나가고 있습니다.