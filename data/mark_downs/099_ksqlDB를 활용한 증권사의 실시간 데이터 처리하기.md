# ksqlDB를 활용한 증권사의 실시간 데이터 처리하기

**Date:** 2024년 7월 17일
**URL:** https://toss.tech/article/ksqldb-realtime-data

---

안녕하세요. 토스증권 실시간 데이터 팀 리더 강병수입니다.

토스증권 실시간 데이터 팀에서는 Kafka, Kafka Connect, Clickhouse, ksqlDB와 같은 서비스에서 발생하는 실시간 이벤트를 다루는 플랫폼을 운영하고 있는데요. 이번 글에서 토스증권 실시간 데이터 프로세싱에 활용 중인 ksqlDB에 대해서 소개하려고 합니다.

## 여는 글

데이터 처리는 처음에는 대부분 배치\(Batch\) 작업으로 시작하지만, 서비스가 고도화되면서 주기적인 배치 성격보다 더 빠른 결과를 원하게 됩니다. 그 시점이 되면 실시간 데이터 처리에 대한 요구가 시작되는데요.

토스증권은 서비스 오픈 전부터 토스에서 쌓아온 플랫폼 구성 및 운영 노하우를 이어받아 시작했습니다. 그 이유로 초기부터 빅데이터 플랫폼이 잘 갖춰져 있었고, 실시간 처리도 충분히 할 수 있었습니다. 다만 플랫폼을 운영하는 사람은 저 한 명이었다는 게 문제였는데요. 이러한 배경에서 실시간 데이터 프로세싱 플랫폼 도입을 고민하던 중 ksqlDB를 선택하게 됐습니다.

토스증권은 서비스 오픈부터 계좌개설 이벤트가 크게 성공하면서 다양한 문제들을 동반했는데요. ksqlDB를 적극적으로 활용해서 문제를 해결해 나간 이야기를 해보려고 합니다.

## 어떤 플랫폼을 고를까? 

처음 실시간 데이터 프로세싱 플랫폼을 도입할 때 어떤 것을 사용할지 고민을 많이 했습니다. 토스에서 사용하던 Spark Streaming, 대중적으로 많이 활용되는 Flink, 그리고 당시 국내에서는 레퍼런스가 거의 없던 ksqlDB가 후보였습니다. Spark Streaming, Flink 모두 좋고 대중적인 플랫폼이지만 세 가지 이유로 ksqlDB를 선택했습니다.

  1. 소스코드 개발 없이 SQL만 이용해서 프로그램을 만들 수 있다는 점

혼자서 많은 실시간 프로세싱 애플리케이션을 개발하기에는 무리였다보니, '생산성'이 가장 중요했어요. 소스코드를 직접 짜는 것과 ksqlDB에서 SQL 기반으로 Job을 만드는 건 생산성에서 10배 이상 차이가 났습니다.

  2. Job 배포 및 모니터링의 단순함

토스에서 Spark Streaming Job을 개발 및 배포할 때 Job이 많아지면 운영에 리소스가 굉장히 많이 들어갔던 경험이 있었습니다. 개발은 끝이 아니라 시작이라는 점 때문에 배포 및 관리가 단순한 플랫폼이 필요했어요.

  3. Kafka Ecosystem에 어울리는 아키텍처

Kafka만 있으면 쉽게 활용이 가능했고, Offset 관리나 H/A 부분을 Kafka에 적극 위임하도록 구현돼 있어서 ksqlDB는 굉장히 Kafka스러운 시스템이라는 생각이 들었습니다. Kafka 운영도 하고 있었다 보니 Kafka에 대한 이해를 바탕으로 잘 운영 해볼 수 있는 장점이 있었어요.

이미지 출처 : <https://developer.confluent.io/courses/inside-ksqldb/streaming-architecture/>

토스증권은 Kafka Ecosystem을 Confluent Platform을 사용하고 있지 않고 [오픈소스](https://github.com/confluentinc/ksql)를 활용하고 있습니다. 그 이유로 ksqlDB를 사용하기 위해서 Confluent에서 Confluent Community 라이선스를 따르는 ksqlDB 소스코드를 활용했는데요. 해당 소스코드를 빌드해서 토스증권의 On-Premise 환경에 ksqlDB 클러스터를 구성해서 사용하고 있어요.

## 토스증권의 ksqlDB 활용 사례

토스증권에서 ksqlDB는 서비스 오픈 이후로 마주한 문제들을 해결해나가면서 규모를 키워나갔어요. 실제 ksqlDB를 통해 문제를 해결해나간 사례들을 소개하면서 ksqlDB의 활용 가능성을 보여드릴게요.

먼저 위 그래프는 현재 토스증권 ksqlDB에 라이브 중인 Job의 개수를 나타내고 있어요. 보이다시피 100개가 넘는 쿼리를 런타임에 유지하고 있습니다. 간단한 실시간 Filter와 Transform Job만 50개 넘게 유지하고 있는데요. ksqlDB를 활용하면 Filter와 Transform은 Where 절과 각종 함수들로 간단하게 개발이 가능합니다. 

이번 글에서는 간단하게 만들 수 있는 사례보다 조금 더 복잡하고 비즈니스적인 가치가 있는 네 가지 사례를 통해 실제 서비스 환경에서 ksqlDB를 어떻게 다양하게 활용하고 있는지 알려드릴게요.

### 사례 \#1: 토스증권 동시 접속자 집계

첫 번째로 소개할 사례는 ksqlDB를 활용해서 만든 토스증권 동시 접속자 집계입니다.

토스 앱 안에 증권 서비스를 오픈하면서 그동안 열심히 서비스 개발을 해낸 동료들이 함께 보고 설렘을 느낄 수 있는 실시간 동시 접속자 집계가 필요했습니다. 배치로 처리하는 것은 역동성이 떨어지다 보니 실시간으로 대시보드를 만들어서 전 임직원이 볼 수 있는 전광판에 게시했어요.

더 중요하게는 당시 사용자가 많던 토스 앱에 하나의 탭으로 증권 서비스가 들어가는 구조였다보니 트래픽 증가 시에도 원활한 서비스를 지속적으로 제공하기 위해 시스템을 운영하는 모든 분들이 실시간 동시 접속자 수를 보며 대응해야 됐어요.

증권 서비스 오픈 당시 실시간으로 데이터를 집계할 수 있는 플랫폼이 ksqlDB 뿐이었으므로, 이걸 활용해서 실시간으로 갱신되는 대시보드를 멋지게 만들어 냈습니다.

실제 전광판에 게시 중인 위 실시간 동시 접속 그래프를 보면 증권사만의 특성이 보입니다. 국내 정규장이 열리는 9시에 유저들이 몰리고, 서머타임 기준 해외 정규장이 열리는 22시 30분에 또 유저가 몰리는 패턴을 볼 수 있어요. 위 그래프를 만들기 위한 KSQL\(이하 KsqlDB 쿼리\)은 아래와 같습니다.
    
    
    CREATE TABLE client_log_example AS
    SELECT `hostname`           AS                           `id`,
           AS_VALUE(`hostname`) AS                           `hostname`,
           TIMESTAMPTOSTRING(WINDOWSTART, 'yyyy-MM-dd HH:mm:ss',
                             'Asia/Seoul')                    `base_time`,
           COUNT_DISTINCT(`user_no`)                          `user_counts`,
           COUNT_DISTINCT(`device_id`)                        `device_counts`
    FROM client_log WINDOW TUMBLING ( SIZE 30 SECONDS )
    GROUP BY `hostname`
    EMIT CHANGES;

굉장히 간단하게 30초 window의 유니크한 동시 접속 유저 수를 집계할 수 있었습니다. 

  * 30초는 내부적으로 정한 window 사이즈이고
  * HyperLogLog 알고리즘을 사용하는 `count_distinct` 함수를 통해 유니크 유저수를 집계 했습니다. 

조금 더 자세하게 설명하면, 동시 접속 유저 수를 판단하기 위해 유저 활동 로그를 30초의 window로 고유한 유저 수를 집계했습니다.

KSQL에서 windowing 기능은 `GROUP BY`와 함께 사용해야 합니다. 구분하는 key 없이 전체 집계를 해야 한다면 '1' 과 같은 상수를 넣어도 됩니다. 위 예시 쿼리 `GROUP BY` key에 `hostname`이라는 필드를 넣은 것은 병렬성을 늘리기 위한 방법으로 추가한 부분입니다.

### 사례 \#2: 환전 서비스

두 번째 사례를 통해 windowing 기능을 조금 더 확장해서 이상 징후를 감지하고 알림을 주도록 만든 사례로 넘어가 볼게요. 토스증권은 해외주식 거래 비중이 높기 때문에 환전 서비스가 중요한데요. 이때 '환율'을 환전 파트너사에서 받아와서 환전 서비스를 제공하고 있습니다. 만약 환전 파트너사에서 '환율'을 잘못 제공해주면 정합성 이슈가 유저에게 전파가 됩니다. 저희 팀에서는 이 부분을 '데이터 정합성 이슈'라고 합니다. 기능상 문제가 아니라 데이터 정합성이 틀어져서 발생하는 것을 의미해요.

돈하고 직결되는 문제인 만큼 중요하기 때문에, 잘못된 것으로 추정된 환율을 환전 파트너사로부터 내려받았을 경우 실시간으로 감지하고 알림을 주도록 ksqlDB을 활용했습니다.
    
    
    CREATE TABLE exchange_example AS
    SELECT bank                                                                as `id`,
           AS_VALUE(bank)                                                      as `bank`,
           LATEST_BY_OFFSET(validFrom)                                         as `valid_from`,
           LATEST_BY_OFFSET(usdMidRate)                                        as `usd_mid_rate`,
           AVG(usdMidRate)                                                     as `usd_mid_rate_avg`,
           ABS((LATEST_BY_OFFSET(usdMidRate) -
                AVG(usdMidRate)) /
               AVG(usdMidRate) * 100)                                          as `usd_mid_rate_gap`,
           TIMESTAMPTOSTRING(WINDOWSTART, 'yyyy-MM-dd HH:mm:ss', 'Asia/Seoul') as `window_start`,
           TIMESTAMPTOSTRING(WINDOWEND, 'yyyy-MM-dd HH:mm:ss', 'Asia/Seoul')   as `window_end`
    FROM exchange WINDOW HOPPING(SIZE 120 SECONDS, ADVANCE BY 10 SECONDS)
    GROUP BY bank
    HAVING (
        ABS((LATEST_BY_OFFSET(usdMidRate) -
        AVG (usdMidRate)) /
        AVG (usdMidRate) *100) >= 2
    )
    EMIT CHANGES;

쿼리를 하나씩 보면, 

  * 먼저 환전 파트너사가 여러 군데이다 보니 `bank`를 `GROUP BY` key로 사용한 걸 볼 수 있습니다.
  * Window size을 보면 2분의 크기로 10초씩 hopping하며 windowing집계를 한다는 것을 볼 수 있고요.
  * 그 밑에는 가장 중요한 `HAVING` 절인데요. 2분 window frame의 평균에 비해서 새로운 값이 2% 이상 높거나 낮으면 '이상 징후'라고 판단하고 결과를 내도록 `HAVING`절을 구성했습니다.

ksqlDB에서도 SQL에서 많이 사용하는 `HAVING`절 활용이 가능하다는 점을 알 수 있습니다. 이렇게 만들어진 결과로 알림을 받아서 문제 발생 시 즉시 이중화 구성된 다른 은행 환율을 사용하는 등의 대응을 하고 있습니다.

### 사례 \#3: 계좌 상태 실시간 확인

토스증권은 Mysql, Oracle, MongoDB의 CDC\(Change Data Capture\) 를 적극적으로 활용하고 있는데요. \([CDC Pipeline 참고 글](https://toss.tech/article/cdc_pipeline)\) ksqlDB는 CDC와도 궁합이 잘 맞습니다. 실시간으로 원천 DB를 Materialized View 형태로 KTable로 만들어 사용하는 방법인데요. 저희는 이 KTable을 실시간으로 발생하는 Stream과 Join해서 다양한 결과들을 만들어 내고 있어요.

예시를 통해 보면 더 명확할 것 같아서 실제 사례를 다시 꺼내볼게요.

주식 주문이 발생하면 해당 주문을 던진 유저의 계좌의 상태를 파악해야 합니다. 계좌의 상태가 주문을 발생시키면 안 되는 경우라면 감지하고 알림을 줘야 하는데요. 실시간 감지가 필요하다 보니 ksqlDB로 알림을 구현을 했습니다.

실시간으로 발생되는 주문 이벤트를 Oracle 원장의 계좌 테이블과 비교해서 계좌의 상태를 확인해야 하는 상황인데요. 만약 이런 기능을 애플리케이션 개발로 구현한다고 하면, 매 로그 건마다 원천 DB에 Select 쿼리를 던져서 확인해야 합니다. 이렇게 구성을 한다면 초당 수만 건씩 발생하는 로그의 경우 원천 DB에 부하를 일으켜 서비스에 영향을 미칠 수 있는 가능성이 높아지는 문제가 있습니다.

CDC를 KTable로 만든다면, 로컬 RocksDB에 원천 DB와 똑같은 형태로 테이블을 유지하기 때문에 이제 더 이상 원천 DB를 괴롭히지 않고 원하는 결과를 얻을 수 있습니다. 주문 Stream과 계좌 KTable을 Join해서 원장 DB로 들어갔어야 할 트래픽을 KTable로 돌려서 read분산을 해낸 모습입니다. 
    
    
    CREATE STREAM account_join_example AS
    SELECT order_stream.acnt_no,
           account_ktable.`id` as `acnt_no`,
           account_ktable.`clnt_no` as `client_no`,
           account_ktable.`buy_trd_stop_yn` as `buy_trd_stop_yn`,
           account_ktable.`sell_trd_stop_yn` as `sell_trd_stop_yn`,
           order_stream.order_side as `order_side`,
           order_stream.guid as `guid`,
           order_stream.order_price as `order_price`,
           order_stream.order_qty as `order_qty`
    FROM order_stream
             JOIN account_ktable ON account_ktable.`id` = order_stream.acnt_no
    WHERE account_ktable.`is_deleted` = 'false'
      AND (account_ktable.`buy_trd_stop_yn`='1' AND order_stream.order_side = 'BUY')
      OR (account_ktable.`sell_trd_stop_yn`='1'  AND order_stream.order_side = 'SELL')
    EMIT CHANGES;

KSQL 쿼리는 KTable과 Stream을 join하고 상태를 비교해서 주문이 발생했는데 이상한 계좌의 경우 메시지를 발생시킵니다. ksqlDB에서 Join 기능 역시 잘 동작한다는 걸 알 수 있어요. 환율 이상탐지와 유사하게 감지해서 알림을 보내주고 대응해나가고 있습니다.

### 사례 \#4: ML의 실시간 Feature

KTable의 이런 재밌는 기능들을 이용해서 ML의 실시간 feature를 만드는 데도 도움을 주고 있는 것을 마지막 사례로 소개드리려고 합니다.

토스증권의 ML팀에서는 유저별로 Clustering한 모델링 결과를 MongoDB에 저장하고 있습니다. MongoDB CDC를 이용해서 유저별 Clustering 결과를 실시간으로 발생하는 유저 활동 로그와 join해서 해당 유저가 어떤 Cluster에 속한 유저인지 실시간으로 태그를 달아주고 있습니다.
    
    
    CREATE STREAM cluster_join_example AS
    SELECT A.`id`,
           A.`user_no`      AS `user_no`,
           A.`log_type`     AS `log_type`,
           A.`section_name` AS `section_name`,
           A.`news_ids`     AS `news_ids`,
           CASE
               WHEN B.`cluster_id` IS NULL THEN -1
               WHEN B.`is_deleted` = true THEN -2
               WHEN B.`is_deleted` = false THEN B.`cluster_id`
           END          AS `cluster_id`
    FROM headline_news A
        LEFT JOIN user_cluster_ktable B ON A.`id` = B.`id` 
    EMIT CHANGES;

쿼리를 살펴보면 이전 예시랑 유사한데요. RDB와 MongoDB 모두 CDC를 KTable로 만들고 join해서 자유자재로 활용이 가능합니다.
    
    
    {
      "user_no": "***",
      "log_type": "impression",
      "section_name": "뉴 홈__뉴스 탭__개인화뉴스__주요뉴스",
      "news_ids": "[\"ajukyung_***\",\"etoday_***\",\"edaily_***\",\"seokyung_***\"]",
      "cluster_id": 1
    }

이렇게 Cluster 태그가 붙은 유저 활동 로그는 사전에 개인정보 처리 동의를 받은 유저에 한해서 개인화된 추천 서비스와 같은 다양한 곳에 활용되고 있습니다.

## ksqlDB 사용 후기

ksqlDB를 잘 사용하면 최소한의 노동력으로 비즈니스에 도움이 되는 실시간 데이터 프로세싱 Job들을 쉽게 만들 수 있습니다. 수 십개가 되는 Job들을 혼자 만들고 관리하는데 큰 어려움이 없었다는 점이 ksqlDB의 큰 장점일 것 같습니다.

물론 불편한 점도 있었는데요. 네 가지 정도 정리해보면 아래와 같아요.

  1. Kafka를 잘 모르고는 활용하기 어려워 러닝커브가 좀 있습니다. SQL 기반이지만 SQL만 아는 것으로는 제대로 KSQL을 만들 수가 없다 보니 다양한 사람들이 자유롭게 실시간 프로세싱 작업을 만들 수 있는 환경을 조성하는 게 어려웠어요.
  2. 비즈니스 요건에 맞춰 로직을 짜기 위해서는 생각보다 창의력이 많이 필요했습니다. 1번의 이야기와 유사한데, Kafka와 ksqlDB를 완벽히 이해하고 그 기반으로 창의력을 동원해서 KSQL을 짜야 원하는 대로 결과물이 나온다는 점이 하나의 허들이었습니다.
  3. Kafka 토픽과 KSQL 형상관리 어려움이 있었어요. Kafka 토픽의 경우 ksqlDB에서 사용하는 내부 토픽들이 많이 생겨서 부담이 좀 있었는데, 이 부분은 저희 팀이 Kafka 클러스터 관리자였다 보니 좀 자유가 있었던 것 같습니다. 다음으로 소스코드가 없긴 하지만, KSQL도 라이브에 배포돼있는 형상이 있기 때문에 KSQL 형상관리가 필요했습니다. GitHub을 이용하고 있기는 한데, 적절한 도구가 없는 점이 불편했어요.
  4. 마지막으로는 관리하기 편한 UI가 없다는 점인데요. 이 부분은 토스증권이 Confluent Platform을 사용하고 있지 않아서 생긴 문제였습니다. 저희는 자체적으로 웹 어드민을 개발해서 활용하고 있습니다.

ksqlDB는 3년이 넘는 시간동안 라이브 서비스에 사용해보니 단점들도 있지만 장점이 너무 명확한 플랫폼이었는데요. 토스증권에는 더 어렵지만 가치 있는 ksqlDB Job들이 있어서 2부에서 더욱 상세한 내용을 공유할 예정입니다. 많은 기대해주세요.