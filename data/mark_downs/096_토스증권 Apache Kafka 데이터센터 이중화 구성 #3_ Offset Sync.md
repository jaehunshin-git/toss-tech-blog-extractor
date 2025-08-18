# 토스증권 Apache Kafka 데이터센터 이중화 구성 #3: Offset Sync

**Date:** 2025년 1월 23일
**URL:** https://toss.tech/article/kafka-distribution-3

---

안녕하세요. 토스증권 실시간 데이터팀 김용우입니다. 이번 글은 토스증권은 Apache Kafka 이중화 구성에 대한 마지막 편으로 [1부 Apache Kafka 이중화 구성에 대한 개요](https://toss.tech/article/kafka-distribution-1), [2부 Active-Active 구성을 기반으로한 양방향 데이터 미러링](https://toss.tech/article/kafka-distribution-2)에 대해 소개해드렸습니다. 마지막으로 3부에서는 Active-Active 구성에서의 consumer offset Sync에 대해서 설명드리고자 합니다.

### Offset이란?

Apache Kafka에서 Offset은 각 Partition 내 메시지의 순서를 나타내는 고유 번호로, 메시지가 들어오는 순서대로 증가합니다. 이는 Kafka가 메시지의 순서를 유지하고 consumer가 데이터를 정확히 처리할 수 있도록 돕는 중요한 메커니즘입니다. Consumer는 마지막으로 읽은 Offset을 저장한 이후에 데이터를 처리하며, 이를 통해 중복 처리와 데이터 손실을 방지합니다.

만약 consumer가 Offset 정보를 잃어버리거나 처음 Kafka에 연결된다면, `auto.offset.reset` 설정에 따라 데이터를 처음부터\(`earliest`\) 또는 마지막부터\(`latest`\) 읽게 됩니다. Offset 관리는 특히 Cluster 이중화 환경에서 필수적입니다. Consumer의 Offset을 정확히 동기화하지 않으면 이미 읽은 메세지를 모두 다시 읽게 되거나, 많은 메세지를 읽지 못하고 넘어간다는 뜻이므로, 빠르고 주기적인 Offset Sync를 통해 consumer offset을 반영해주는 것이 필수적입니다. 

토스증권에서 구현한 방법에 들어가기 앞서, Kafka 이중화 도구로 잘 알려진 Kafka MirrorMaker2과 Confluent 사의 Replicator에 대해서 간략하게 설명해보고자 합니다.

### 기존 Offset Sync 방식 \#1 - Kafka MirrorMaker 2 \(MM2\)

먼저 Kafka MirrorMaker2\(이하 MM2\)는 Apache Kafka에서 제공하는 Kafka 이중화 도구입니다. MM2는Data Mirror를 담당하는 MirrorSourceConnector와 Offset Sync를 담당하는 MirrorCheckpointConnector로 구성되어 있습니다. 

MirrorSourceConnector에서 Data Mirror를 진행함과 동시에, Source Record의 offset과 Target Cluster로 Mirror한 Record의 offset을 각각 `upstreamOffset`, `downstreamOffset`이라는 이름으로 OffsetSync Topic에 기록합니다. Record를 Produce했을 때 받는 `ProduceResponse`에 담겨있는 Offset 정보를 OffsetSync Topic에 기록한다고 생각해주시면 됩니다. \([default로 100 record 당 한 번 기록합니다](https://kafka.apache.org/documentation/#mirror_source_offset.lag.max)\) 아래의 예시는 test topic의 0번 partition에 offset 5000의 Record가 Target Cluster의 test topic 0번 partition에 10000 offset으로 미러되었다는 것을 의미합니다.
    
    
    {
    	"topicPartition": "test-0",
    	"upstreamOffset": 5000,
    	"downstreamOffset" : 10000
    }

MM2의 MirrorCheckpointConnector에서는 이 OffsetSyncTopic에서 offset 매칭 정보를 가져와consumer offset을 Target Cluster에 맞게 변환합니다. 원리는 간단하게 두 가지입니다. 

  1. Upstream에서 현재 source offset보다 작거나 같은 offset 중 제일 큰 `offsetSync` 정보를 찾는다.
  2. 현재 source offset과 같다면 해당 OffsetSync의 downstream offset \(target Cluster의 offset\)을 그대로 사용하고, 현재 source offset보다 크다면 downstream offset에 1을 더하여 사용한다. 
  3. 2 과정에서 계산한 downstream offset을 target Cluster에 sync한다.

MM2에서는 consumer offset이 OffsetSync Topic에서 찾은 upstream값과 정확히 같지 않다면, 그 차이가 얼마든지 downstream에서 1만 더해, 즉 바로 다음 offset을 사용하는 아주 보수적인 방식을 채택하였습니다. 

간단하게 예시를 들어 설명해보겠습니다. 

위와 같이 upstream, downstream offset이 OffsetSync Topic에 저장되어 있을 때를 고려해보겠습니다. Source offset이 100인 경우, 작거나 가장 큰 OffsetSync 정보인 \(upstream 100, downstream 200\)을 가져옵니다. 이때 source offset 100이 OffsetSync정보인 \(upstream 100, downstream 200\)의 upstream offset과 같으므로 downstream offset 200을 그대로 target cluster에 sync해주면 됩니다. 

만약 source offset 199을 target cluster로 변환하려고 한다면 어떨까요? 이전과 동일하게 작거나 같은 가장 큰 OffsetSync 정보인 \(upstream 100, downstream 200\)을 가져오게 됩니다. Source offset이 OffsetSync 정보와 동일하지 않으므로, 200 + 1인 201을 target cluster에 기록하게 됩니다. 이러한 상황에서 우리는 199라는 source offset은 target cluster에서 299 혹은 그 근방이지 않을까 으레 추측할 수 있습니다. 하지만 MM2에서는 보수적인 방식을 채택하여 299가 아닌, 201로 offset을 변환하게 됩니다.

이는 OffsetSync Topic을 활용한 구조에서 중복은 발생하더라도 절대 유실이 발생하지 않게 하기 위한 방식으로 소스코드에서도 주석으로 잘 설명해주고 있습니다. 
    
    
    // If the consumer group is ahead of the offset sync, we can translate the upstream offset only 1
    // downstream offset past the offset sync itself. This is because we know that future records must appear
    // ahead of the offset sync, but we cannot estimate how many offsets from the upstream topic
    // will be written vs dropped. If we overestimate, then we may skip the correct offset and have data loss.
    // This also handles consumer groups at the end of a topic whose offsets point past the last valid record.
    // This may cause re-reading of records depending on the age of the offset sync.
    // s=offset sync pair, ?=record may or may not be replicated, g=consumer group offset, r=re-read record
                // source |-s?????r???g-|
                //          |  ______/
                //          | /
                //          vv
                // target |-sg----r-----|

이런 방식을 사용해서 MM2는 유실이 발생하지 않는 Offset Sync를 구성했지만, 세 가지 한계가 생겼습니다.

  1. `1 / 100 (OffsetSync Topic에 기록하는 Record의 주기)`의 확률로 OffsetSync를 정확하게 찾아낼 수 있고 그 경우에만 정확한 Offset Sync가 가능하며, 그 이외에는 중복이 발생하게 됩니다. 
  2. 양쪽 Cluster에 동일한 Topic명을 생성하여 Mirror하는 환경에서는 사용이 제한적입니다. 
  3. Offset Sync가 Data Mirror의 결과물인 OffsetSync Topic을 활용하기 때문에 Data Mirror가 없는 Topic에서는 Offset Sync를 지원하지 못합니다. 예를 들어, A Cluster에서 B와 C Cluster로 각각 데이터를 복제하는 환경에서 B에 있는 consumer offset을 C로 반영하려고 할 경우, B와 C간의 Offset Sync 정보가 저장되어있지 않기 때문에, Offset Sync가 불가능합니다. 

### 기존 Offset Sync 방식 \#2 - [Confluent Replicator ](https://docs.confluent.io/platform/current/multi-dc-deployments/replicator/replicator-failover.html#consumer-offset-translation-feature:~:text=of)

Confluent 사에서 판매하는 Confluent Replicator에서도 Offset Sync와 관련된 기능을 제공하고 있습니다. Offset Translation이라는 이름으로 제공하는 이 기능은 오픈소스 기반의 Apache Kafka에서는 사용할 수 없는 방법입니다. 

Confluent에서 제공하는 `Confluent Kafka Consumer` 와`Consumer Timestamps Interceptor` 를 사용하는 방법으로 오픈소스 방식에 없는 추가적인 기능들을 사용합니다. Apache Kafka 환경에서 Consumer Offset을 commit하면 `__consumer_offsets` topic에 Consumer가 읽은 가장 마지막 offset 정보가 저장되는 것과 다르게, Confluent에서는 commit 시점에 `__consumer_timestamps` topic에 offset 정보와 더불어 해당 메세지의 timestamp까지 함께 저장하도록 합니다. 이 offset과 timestamp를 바탕으로 아래와 같은 순서로 Offset Sync를 진행합니다.

  1. Source Cluster에서 `__consumer_timestamps` 에 offset과 timestamp를 저장
  2. Replicator에서 Consumer의 최신 offset과 timestamp를 조회
  3. Target Cluster에서 `offsetsForTimes` 함수를 사용하여 timestamp에 맞는 offset을 검색
  4. 검색된 offset을 Target Cluster에 Commit

Confluent Replicator는 이러한 방식으로 Consumer Offset을 읽어올 때 Timestamp 정보를 함께 가져오고, 이를 통해 간편하게 Target Cluster에서 알맞은 offset을 가져오게 됩니다. MM2와 같이 Data Mirror에서 OffsetSync Topic으로 데이터를 넣어주고 이를 활용하는 방식이 아니기 때문에, Data Mirror가 직접적으로 진행되지 않는 환경에서도 Offset Sync가 가능합니다. OffsetSync Topic의 관리 또한 필요하지 않아 더 간편하게 Offset Sync를 관리할 수 있다는 장점도 존재합니다. 

Confluent Replicator의 한계점은 명확합니다. `Consumer Timestamp Interceptor`와 같은 Apache Kafka 기반이 아니라 Confluent Kafka 환경에서 제공하는 Kafka를 구매해 사용해야 합니다. 구매하지 않고 직접 구축해 사용하기 위해서는 Apache Kafka Consumer에 추가 기능을 달아 개발하고, 검증하여 이를 전사의 Kafka Consumer들에게 배포하여합니다. 이는 매우 오랜 시간이 걸리는 일이고, 많은 리스크를 가지고 있습니다. 

### 토스증권의 Offset Sync

토스증권 Offset Sync의 핵심 시스템 요구사항은 두 가지입니다.

  1. 재난 상황 시, 중복은 최소화하되, 유실은 절대 발생하면 안 된다
  2. 작업 상황 시, 중복과 유실이 모두 없는 환경을 제공할 수 있어야 한다.

중복 : Consumer가 이미 읽은 데이터를 다시 읽음

유실 : Consumer가 읽지 않은 데이터를 건너뜀

화재, 침수 등으로 데이터센터에 문제가 발생해 Kafka Cluster 전체를 다른 데이터센터로 이동해야 하는 재난 상황과 장비 점검, 데이터센터 작업 등 계획된 일정에 의해 Kafka Cluster 일부를 다른 데이터센터로 이동시켜야 하는 작업 상황입니다. 

Kafka 이중화 상황에서 발생할 수 있는 두 가지 문제가 존재합니다. 바로 중복과 유실입니다. 여기서 중복과 유실은 Data Mirror로 인해 데이터가 중복 혹은 유실된 것이 아닌, Offset Sync를 통해 발생한 중복과 유실을 의미합니다. Consumer가 한 번 읽은 데이터를 다시 읽거나, 읽지 않은 데이터를 건너뛰는 것을 의미합니다. 

모든 경우에 유실은 발생하면 안 됩니다. 유실은 서비스 신뢰성을 근본적으로 훼손하게 되므로 반드시 방지해야 합니다. 중복은 각 사용자들이 멱등성을 보장하는 서비스를 구축하여 보완할 수 있지만, 유실은 서비스에서 대처할 수 있는 방안은 존재하지 않습니다. 반드시 Kafka 수준에서 방지해야 하는 문제입니다. 

계획된 작업 상황 시에는 중복 또한 제거해주어야 합니다. 급박하게 발생한 재난 상황에는 중복을 발견하고 처리할 시간과 방법이 부족하지만, 계획적으로 수행되는 작업 상황에서는 중복 또한 감지하고 처리할 수 있는 구조를 만들어 신뢰할 수 있는 작업 환경을 보장해주어야 합니다. 

저희는 이 두 가지 상황에 대한 요구사항을 달성할 수 있는 Offset Sync가 필요하였습니다. 아쉽게도 위에서 살펴본 두 방식 모두 토스증권이 사용하기에는 적합하지 않습니다. 저희는 저희의 환경에 맞는 Offset Sync를 구현할 필요가 있었습니다. 

재난, 작업 두 가지 상황에 대한 요구사항은 Topic에 데이터가 어떻게 들어오는지에 따라 달성하는 방식이 달라지게 됩니다. 토스증권의 Active-Active 아키텍처에서 나타나는 두 가지 Topic의 형태와 그에 따라 Offset Sync를 구현한 두 가지 방식 Timestamp 검색 방식과 Header 참조 방식에 대해 설명드리도록 하겠습니다.

### Topic의 형태

1,2편을 통해 소개드린 저희의 Active-Active 아키텍처를 Topic 레벨로 자세히 살펴보면 크게 두 가지 형태로 사용되는 것을 확인할 수 있습니다. 하나는 양쪽 Cluster의 Topic에 각각 50%의 데이터가 들어오고 Data Mirror를 통해 복제되어 100%의 데이터를 모두 가지고 있는 구조\(50:50 구조라 칭함\). 다른 하나는 한쪽 Cluster의 Topic에 100%의 데이터가 들어오고 Data Mirror를 통해 다른 Cluster의 Topic에 데이터가 전달되는 구조\(100:0 구조라 칭함\)입니다. 50:50구조와 100:0구조는 Topic 사용자들의 다양한 이유에 의해 결정되기 때문에, 저희는 이를 모두 지원해줄 필요가 있습니다. 토스증권에서는 핵심 요구사항 두 가지를 만족하기 위해, 50:50구조와 100:0 구조에서 각기 다른 Offset Sync 방식을 택하고 있습니다. 

### Offset Sync Strategy \#1 - Timestamp 검색 방식

먼저 소개해드릴 방식은 100:0 구조에서 사용하는 Timestamp 검색 방식입니다. 이 방식은 Confluent Replicator에서 `consumer interceptor`와 `__consumer_timestamp` Topic를 활용하여 Timestamp를 기반으로 offset을 찾아내던 방식을 Apache Kafka 환경에 맞게 개발한 것입니다. Kafka는 각 Topic의 partition에서 record를 저장할 때, offset과 timestamp를 함께 기록합니다. 이를 통해 Kafka는 record의 순서를 보장하는 동시에, 특정 시간에 해당하는 record를 효율적으로 조회할 수 있는 기능 `offsetsForTimes`를 제공합니다. 

Timestamp를 활용한 Offset Sync의 흐름은 다음과 같습니다. 

  1. Source Kafka Cluster의 consumer offset을 읽어온다.
  2. consumer offset에 해당하는 Record를 Consume하여 해당 Record의 Timestamp를 확인한다.
  3. Target Kafka Cluster에서 Kafka Consumer의 `offsetsForTimes` 함수를 사용하여 해당 Timestamp를 통해 offset을 검색한다.
  4. 해당 offset을 Target Kafka Cluster의 consumer의 offset으로 commit한다.

간략하게 설명하여 Source, Target Cluster 간의 검색을 위한 key로 timestamp를 활용하여 offset을 찾아내는 방식입니다. Mirror된 Record는 동일한 Timestamp를 가지고 있기 때문에, Timestamp를 이용해 검색하면 손쉽게 offset을 찾아낼 수 있는 것처럼 보이고, 유실과 중복 역시 발생하지 않을 것처럼 보입니다. 하지만 `offsetsForTimes` 함수의 맹점이 하나 존재합니다. 바로 `offsetsForTimes` 함수는 해당 Timestamp보다 같거나 큰 Timestamp를 가진 첫 offset을 출력한다는 점입니다. 

우리가 생각하는 일반적인 Topic의 Timestamp는 이렇게 증가하는 모습입니다. 더 늦게 들어온 Record는 더 큰 Timestamp를 가지고 있고 계속해서 증가하고 있죠.

이러한 경우에는 Timestamp 검색 방식으로 Offset을 적절히 찾아내는 것을 확인할 수 있습니다. 

하지만 서비스 환경에서 Topic들을 살펴보면 꼭 이렇게 증가하는 형태를 띄지 않는 경우들도 있습니다. 동일하게 여러 Timestamp가 들어올 수 있고 \(주로 Batch Job\) 어떤 경우에는 더 큰 Timestamp가 앞선 offset으로 나타날 수 있습니다. 이는 Topic의 특성에 따라 달라지는 것이기 때문에, Timestamp가 반드시 순차적으로 증가할 것이라고 보장할 수 없습니다. 

이 경우 어떻게 될까요? 

`offsetsForTimes` 함수가 찾으려던 offset\(10:00:02\)보다 큰 Timestamp\(10:00:03\)가 작은 offset을 가지고 있어, 더 이전의 offset\(102\)을 검색 결과로 내놓게 됩니다. 목표했던 offset보다 더 작은 offset을 Target Cluster의 consumer offset으로 commit하게 되어 이때 Consumer를 Target Cluster로 옮긴다면 중복이 발생하게 됩니다. 더 작은 offset을 검색하는 경우만 발생하기 때문에 유실이 발생하는 구조는 아니게 됩니다. 

이로 인해 재난, 작업 상황 모두 데이터가 증가하며 들어오는 일반적인 상황에는 데이터의 중복, 유실이 모두 없는 구조, 동일한 Timestamp가 연달아 들어오거나 Timestamp가 꼬여 들어오는 경우에는 중복이 발생할 수 있는 구조라고 할 수 있습니다. 

작업 시 Timestamp의 순서가 꼬이지 않아 중복이 없다는 것을 어떻게 판단할 수 있을까요? 사실, 일반적인 Kafka Topic에서는 Timestamp의 순서가 꼬이는 일이 드물지만, Offset Sync 과정에서는 이 가능성을 완전히 배제할 수는 없습니다.

저희는 Offset Sync 과정에서 Source Cluster의 Offset에 해당하는 메시지를 읽을 때, Timestamp 순서가 꼬여서 중복이 발생할 수 있는 경우를 감지하기 위해 자체적으로 개발한 메트릭을 활용하고 있습니다. Source offset의 Timestamp보다 더 큰 Timestamp를 검색하게 되는 상황이 발생하면, 이를 메트릭으로 기록하고 시각화하여 즉시 감지할 수 있도록 합니다. 이러한 방식은 작업 중 Timestamp의 순서가 꼬여 중복 데이터가 발생할 가능성을 미리 파악하고, Topic별로 적절히 대처할 수 있는 기반을 제공합니다.

Confluent Replicator와 같은 도구도 Offset Sync 과정에서 Timestamp 검색 방식을 사용하지만, 저희는 이를 발전시켜 중복 발생 가능성을 실시간으로 모니터링하고, 이를 기반으로 적절히 대응할 수 있는 체계를 구축했습니다. 메트릭은 단순한 감지에 그치지 않고, 작업 전에 문제가 발생할 가능성이 있는 Topic을 사전에 분석하고 처리할 수 있는 유연성을 제공합니다.

그렇다면 이 방법을 100:0 환경뿐만 아니라 양방향으로 데이터를 Mirror하고 있는 50:50 환경에서도 적용해보면 어떨까요?

50:50 구조와 100:0 구조의 가장 큰 차이점은 양방향 미러링 과정에서 메시지의 순서가 바뀐다는 점입니다 입니다. 100:0 환경에서는 Source Kafka Cluster의 Topic에서 Target Kafka Cluster의 Topic으로 동일한 순서로 message를 전달합니다. 토스증권에서는 양 Cluster의 Topic이 동일한 Partition수를 가지고, 동일한 Partition으로 들어가는 것을 보장합니다. 즉 양 Cluster에서 동일한 Topic은 Partition 단위로 동일한 메세지 순서를 가진다는 것을 의미합니다. 이를 통해 Timestamp 검색 방식을 구축할 수 있었습니다. 

하지만 50:50구조에서는 양 클러스터 같은 토픽의 메시지 순서가 다를 수 있습니다. 데이터가 연속적으로 들어오고 있는 Topic은 양방향 미러링을 하는 과정에서 데이터의 순서가 달라지게 됩니다. 

동일한 Cluster에서 발생한 메세지들 간의 순서는 같다고 할 수 있지만 \(위의 그림에서 1→2→3→4, A→B→C\) Topic 단위로 살펴보면 양 Cluster의 메세지 순서는 차이가 발생합니다. 이러한 상황 속에서 Timestamp 검색 방식을 사용한다면 어떻게 될까요?

Source Cluster에서는 메세지 3까지 Consume하였습니다. Timestamp 검색 방식으로 Target Cluster에서 메세지 3를 찾아내었고, 이를 consumer offset으로 commit하였습니다. 만약 이때 Source Cluster에 장애가 발생해 Target Cluster로 Consumer를 이전하게 되면 어떻게 될까요? A B C 메세지는 아직 Source Cluster에서 Consume하지 않았습니다. 하지만 메세지의 순서가 꼬여 메세지 3을 읽었다고 commit하니 Target Cluster에서는 4부터 Consume하게 되어 A,B,C를 consume하지 않고 건너뛰는 상황이 발생합니다. 이런 상태에서 consumer를 Target Cluster로 넘기게 된다면 이는 유실로 이어집니다.

### Offset Sync Strategy \#2 - Header 참조 방식

50:50구조에서 Timestamp를 사용할 경우, 유실이 발생한다는 것을 확인했습니다. 다시 되새겨보는 저희의 요구사항은 중복이 발생하더라도, 유실이 없는 환경을 구축하는 것입니다. 그렇다면 50:50 구조에서 어떻게 유실 없이 Offset Sync를 할 수 있을까요? 

50:50 구조에서 순서가 꼬여 문제가 발생하는 경우를 좀 더 해부해보겠습니다. 1,2,3과 같이 consumer offset이 Source Cluster에서 Produce된 데이터라면 해당 offset을 찾아냈을 경우, A,B,C를 건너뛰어 유실이 발생합니다. 하지만 A,B,C가 consumer offset일 경우, TargetCluster에서는 유실이 발생하지 않죠. 다만 1,2,3이 중복이 됩니다. 

동일한 Cluster에서 들어온 데이터는 동일한 순서를 지키는 것이 보장되므로 위의 1,2,3 / A,B,C와 같이 동일한 Cluster에서 들어온 데이터를 하나의 Group으로 묶을 수 있습니다. 이러한 두 Group간의 양상은 아래처럼 두 가지로 나타날 수 있게 됩니다. 

아래와 같이 동일한 순서로 나타난다면 1의 offset을 1’로 찍어주거나, A’의 offset을 A로 찍어주는 것 모두 가능합니다. 

하지만 이와 같이 Group의 순서가 뒤집힌 상황에서는 양상이 다르게 나타납니다.

오른쪽 그림과 같이 A’으로 Offset Sync하는 경우 1’을 읽지 않는 것으로 처리하여 중복, 1으로 Offset Sync하는 경우 A가 읽은 것으로 처리되어 유실이 발생하게 됩니다. 즉 target cluster에서 미러링한 메세지만 Offset Sync해준다면 X자로 데이터가 꼬여서 들어온 상황에서 중복은 발생하지만 유실은 발생하지 않음을 의미합니다. 

따라서 저희는 Offset이 Target Cluster에서 Mirror된 메세지의 Offset일 경우때만 Offset을 Mirror를 하도록 구현해보았습니다. 메세지가 Target Cluster에서 온지 확인하는 방법은 간단했습니다. 이전 편 [데이터 미러링](https://toss.tech/article/kafka-distribution-2)에서 소개드린 바와 같이 토스증권에서는 Data Mirror 구현에서 메세지의 Header에 해당 메세지의 Offset을 기록하여 전송하도록 하였습니다. 
    
    
    "IDC" : IDC2
    "Offset" : 1234516

이 메세지 Header를 통해 Target Cluster에서 Mirror된 메세지인지, Target Cluster에서 어떤 Offset을 가지고 왔는지 단 번에 알 수 있습니다. 이걸 활용해 Header에 적힌 Offset대로 Target Cluster의 consumer offset을 commit해주게 됩니다. 

이전 편들에서 설명드렸다시피, 토스증권에서는 Kafka Producer가 splitDNS의 주소를 통해 데이터를 Produce하고 이 SplitDns 50:50으로 Load Balancing하여 넣어주게 됩니다. 이를 통해 두 Kafka Cluster에 데이터가 50%씩 각각 들어가게 되고, 이를 Data Mirror로 복제하여 100%의 데이터를 각 Cluster에 넣어주게 됩니다. 

즉 한 Topic의 데이터는 50% 확률로 Data Mirror를 통해 반대 Cluster에서 들어온 데이터이고, 이는 50% 확률로 Header를 가지고 있다는 것을 의미합니다. 더 나아가 50% 확률로 Offset Sync를 수행될 수 있음함을 의미합니다. 

매 주기마다 Offset Sync가 되는 것도 아니고, 50% 확률로 Offset Sync가 수행될 수 있다는 점에 긴 지연이 발생할 수 있다는 것처럼 느껴집니다. 하지만 30초 주기로 Offset Sync를 실행한다면 5분간 총 10번의 Offset Sync를 시도하고, 모두 실패할 확률은 2^10분의 1 약 0.1%의 확률로 5분 간 Offset Sync가 되지 않을 확률은 대단히 낮습니다. 

추가적으로 Header를 통해 Offset을 찾아오는 확률을 높여주기 위해, consumer offset뿐만 아니라 해당 메세지를 기준으로 최신 Record를 N건을 Consume하여 Header가 나오는 메세지를 찾는 방식을 적용하였습니다. 이를 통해 Offset Sync의 확률은 65-70% 수준으로 높일 수 있게 되었습니다. 

Header 참조 방식을 사용하면 Offset Sync의 수행확률을 낮춘 대신 유실을 제거할 수 있었습니다. 하지만 여전히 중복이 발생할 수 있고, 그렇다면 저희의 핵심요구사항 2번인 “작업 상황 시, 중복과 유실이 모두 없는 환경을 제공할 수 있어야한다.”를 만족하지 못한다는 뜻이 됩니다. 작업 상황 시 중복 없는 환경을 제공하려면 어떻게 해야할까요? 

Header 참조 방식에서 중복이 발생하는 원인인 데이터가 X로 꼬여있는 현상을 제거해주면 됩니다. Split DNS를 통해 50:50으로 나누어 전송하던 비율을 0:100으로 변경하여 모든 데이터를 Target Cluster로 전송합니다. 이후 잠깐의 시간이 지나면 Source Cluster의 모든 데이터는 Target Cluster에서 Mirror된 데이터가 되고, 데이터의 X자 꼬임이 해소됩니다. 이때부터 유실, 중복이 모두 없는 Offset Sync를 제공할 수 있게 됩니다. 

Header 참조 방식이 잘 해결하지 못하는 일부 Topic들이 존재합니다. 바로 데이터가 오랜 기간 발생하지 않아 Offset Sync가 드물게 수행되는 Topic들입니다. 극단적인 예를 들어보자면 데이터가 1시간에 한 건 발생하는 Kafka Topic이 있고, 이때 Message가 6시간 연속 Source Cluster로 들어간다면, Offset Sync에서는 6시간 동안 Header를 찾지 못해 Offset Sync 지연이 6시간이 되어버립니다. 저희는 오래 데이터가 발생이 되지 않았고 Consumer lag도 0인 채로 있는즉, Data Mirror도 Consume도 발생하지 않는 Topic들에 대해서 Target Topic의 Consumer Offset을 최신으로 유지하는 방식으로 보완하여 이 문제를 해결하고 있습니다.

정리하자면 Header 참조 방식은 50:50 구조에서 Target Cluster에서 Mirror된 데이터만 Offset Sync를 실행함으로써 유실이 없도록 구현, 작업 상황 시 데이터 인입을 Target Cluster로 몰아주는 운영을 통해 중복이 없도록 구현하였습니다. 추가적으로 데이터가 오래 발생하지 않아 Offset Sync가 지연되는 Topic들을 최신화해주어, 기존의 도구들로 충족할 수 없는 예외적인 케이스들도 보완하였습니다.

### 모니터링

마지막으로 Offset Sync가 잘 진행되고 있는지를 확인하는 두 가지 모니터링에 대해서 설명드리며 글을 마치도록 하겠습니다. 

주요 모니터링은 총 두 가지입니다. 하나는 Kafka Cluster 전체적으로 Mirror가 잘 되고 있는지 한눈에 확인할 수 있는 그래프, 다른 하나는 각 Topic, Consumer별로 현재까지 읽은 offset 현황을 확인할 수 있는 대시보드입니다. 

먼저 그래프를 만들기 위해 Offset Sync가 잘 진행되고 있을 때, 양 Cluster의 consumer offset이 어떻게 변화할지 생각해보도록 하겠습니다. Source Cluster의 consumer offset은 사용자들이 데이터를 Produce하고 Consume해가며 서비스가 활발하게 동작하고 있기 때문에 시간이 지남에 따라 증가할 것입니다. Offset Sync가 일정한 주기로 잘 수행되고 있다면, Target Cluster의 consumer offset은 아래와 같이 주기적으로 Source Cluster의 consumer offset을 따라갑니다. 또한 Source Cluster의 consumer offset과 TargetCluster의 consuemr offset은 동일한 양의 데이터가 인입되기 때문에 일정한 상수만큼 차이가 날 것입니다. 

이때 Source Cluster의 consumer과 Target Cluster의 consumer 간의 offset 차이는 어떻게 나타날까요? Offset Sync가 수행된 직후에는 상수 차이로 떨어졌다가 다음 Offset Sync가 수행될 때까지 증가하는 모습을 보일 것입니다. Source Cluster의 consumer offset은 증가하는데 비해, Target Cluster의 consumer offset은 Offset Sync가 수행되지 않는 동안 변화하지 않기 때문입니다. 

그렇다면 Source Cluster와 Target Cluster의 consumer offset 차의 변화량은 어떻게 될까요? Offset Sync의 주기까지 증가하였다가 Offset Sync가 완료되면 다시 동일한 양으로 감소되어야 할 것입니다. Source Cluster에서 증가한 consumer offset만큼 Offset Sync에서 Target Cluster의 consumer offset에 적용해주기 때문에 동일한 양으로 감소하게 됩니다. 따라서 차의 변화량은 동일한 폭으로 늘었다가 줄었다를 반복하게 됩니다. Offset Sync의 주기보다 큰 window를 합한다면 동일한 증가와 감소가 같이 포함되기 때문에 해당 window의 변화량의 합은 0에 수렴하게 됩니다. 

복잡하게 과정이 있는 것처럼 보이지만 목표하는 바는 간단합니다. 시간 t에 대하여 Source Cluster의 consumer offset을 f\(t\), Target Cluster의 consumer offset을 g\(t\), 두 Cluster의 일정한 상수 차이를 C, Offset Sync의 주기로 인해 발생하는 Source consumer offset과 Target consumer offset의 차를 D\(t\)라고 두면, 아래와 같은 식을 만족합니다. 

따라서 Offset Sync가 정상적으로 진행 중인 환경에서는 “Source Cluster의 consumer offset과 Target Cluster consumer offset의 차의 변화량이 일정한 window로 0에 수렴” 하게 됩니다. 토스증권에서는 Kafka에서 발생한 다양한 metric들을 Clickhouse에 적재, 이를 Grafana와 연동하여 복잡한 Query를 통한 조회도 가능한 환경이 구축되어 있습니다. 이를 통해 위의 수식을 그래프로 나타내면 다음과 같습니다.

초록색 그래프은 두 Cluster의 consumer offset의 차의 변화량 \(위 수식에서 3번째 식\)을, 노란색 그래프은 그 변화량의 10분 window의 sum \(위 수식에서 4번째 식\)을 나타냅니다. 위에서 설명드린 대로 초록색 그래프, consumer offset의 차의 변화량은 source에서 증가한 offset만큼 target에서 따라잡기 때문에 0을 기준으로 동일한 폭으로 증가, 감소를 반복하는 모습을 보입니다. 그리고 노란색 그래프, 10분 window에서 해당 변화량의 합은 Offset Sync를 통해 offset이 변화하지 않았기 때문에 0에 수렴하는 것을 확인할 수 있습니다. 저희 이 노란색 그래프가 0에 수렴하고 있는가만 확인하면 됩니다.

반대로 Offset Sync가 제대로 동작하지 않는 상황에서는 아래와 같이 그래프가 점차 증가하는 것을 보입니다. 

저희는 이 그래프를 Cluster 전체와 consumer 별로 각각 적용하여 전체 Offset Sync 현황과 각 consumer별 Offset Sync 현황을 한눈에 파악할 수 있도록 하였습니다. 

두 번째는 당연하게도 각 Topic과 consumer 별 Offset Sync의 디테일한 상태를 파악하는 대시보드가 필요합니다. 내 Topic이 어떤 형태의 Topic인지, 현재 Data Mirror가 수행 중인지, consumer는 Offset Sync가 수행되고 있는지, consumer offset이 양 cluster에서 얼마나 차이 나는지 등을 나타내고 있습니다. 이 대시보드를 통해 지연이 발생하는 Topic과 consumer를 탐지하여 개선하고 있습니다. 또한 Data Mirror와 Offset Sync가 모두 잘 수행되는 중이라면 Mirroring으로, 그중에서도 consumer offset과 그 메세지의 내용까지 완벽히 동일한 경우는 InSync로 Status를 나타내어 consumer 이동을 위한 신호로 사용하고 있습니다. 

아래는 이 대시보드를 통해 consumer의 상태를 함께 모니터링하며 작업한 메세지의 일부를 발췌한 내용입니다. Timestamp 검색 방식을 활용하는 Topic들에 대한 작업으로, Mirroring 상태의 consumer들을 종료하여 InSync가 되는지 확인하고, 이 신호에 맞춰 consumer 이전 작업을 실시하였습니다. 이런 방식으로 대시보드를 활용해 consumer의 kafka cluster 이전을 중복,유실없이 해내고 있습니다.

### 마치며

이 글에서 토스증권의 Offset Sync를 소개하는 것을 마지막으로 토스증권의 Apache Kafka 데이터센터 이중화 구성에 대한 이야기가 마무리되었습니다. 토스증권의 많은 서비스들이 MSA로 설계되어 Apache Kafka를 메세지 브로커로 사용하고 있습니다. 

이러한 환경에서 저희 실시간데이터팀은 Apache Kafka의 견고한 이중화설계를 통해, 재난 상황에도 유실없이 데이터를 제공할 수 있는 안전성과 서비스들이 여러 데이터 센터를 넘나드는 자유를 모두 제공하고자 하였습니다. 앞으로 더 견고하고 자유로운 토스증권이 되기 위해 노력할 것이며, 많은 여정들을 여러분들께 소개해드리도록 하겠습니다. 많은 관심 부탁드립니다. 긴 글 읽어주셔서 감사합니다.