# 토스가 다양한 ML 모델을 만드는 법: Feature Store & Trainkit

**Date:** 2025년 8월 14일
**URL:** https://toss.tech/article/feature-store-trainkit

---

안녕하세요. 토스 ML Platform 팀에서 다양한 ML 서비스를 위한 플랫폼을 개발하고 있는 우종호, 송석현입니다.

토스에는 다양한 비즈니스 도메인에 걸쳐 수많은 ML 기반 서비스가 존재합니다. 신용평가, 이상거래탐지, 마케팅 최적화, 고객 경험 개선 등 서비스마다 요구하는 ML 컴포넌트도 각양각색입니다. 이러한 서비스들이 빠르게 실험하고 안전하게 배포되기 위해서는 안정적이고 유연한 MLOps 플랫폼이 필수적이죠. 저희 팀은 이러한 요구를 충족시키기 위해 Feature Store, Model Registry, Training Pipeline, Model Serving 등 핵심 구성요소들을 오픈소스 및 자체 개발하여 구축하고 있습니다.

이번 시리즈에서는 그 중에서도 특히 모델 학습과 Feature 관리에 핵심이 되는 Feature Store와 이를 활용한 학습 파이프라인 자동화를 위한 도구인 Trainkit을 소개해드리며, ML 실무 환경에서 반복되는 문제들을 어떻게 체계적으로 해결해 나가고 있는지를 공유드립니다.

이 글을 통해 ML 플랫폼을 직접 설계하거나, 조직 내 MLOps 체계를 고민하고 계신 분들에게 조금이나마 실질적인 인사이트를 드릴 수 있기를 기대합니다.

## Feature Store & Trainkit

ML 모델을 서비스로 운영하는 과정은 단순히 모델을 개발하는 것에서 끝나지 않습니다. 데이터 수집, Feature 관리, 학습 파이프라인 구성, 모델 배포, 모니터링 등 모델 전 생애주기를 안정적이고 일관되게 운영할 수 있는 체계가 필요합니다. 이러한 과정을 자동화하고 재현 가능하게 만드는 것이 바로 MLOps의 핵심이며, 이는 ML 서비스의 실질적인 성능과 운영 효율성을 좌우하게 됩니다.

토스 ML Platform 팀은 그 중에서도 모델 학습과 Feature 관리를 정형화하고, 학습-서빙 간 불일치\(Training-Serving skew\)를 방지하며, 실험 효율성을 극대화하기 위해 Feature Store와 Trainkit을 자체적으로 개발해왔습니다.

이 도구들은 단순한 기술적 구현을 넘어서, ML 개발의 일관성과 재현성을 보장하고 조직 전체의 협업 효율을 높이는 기반 인프라로써 자리 잡아가고 있습니다.

## Feature Store 란?

MLOps Cycle의 컴포넌트별로 Feature Store와의 Interaction \(출처: <https://feast.dev/blog/what-is-a-feature-store/>\)

위 다이어그램은 모델을 서비스에 반영하는 과정에서 Data Engineer, Data Scientist, ML Engineer들이 수행하는 작업과 모델 학습, 서빙, 모니터링 사이에서 Feature Store 가 어떻게 상호작용하는지를 보여주고 있습니다. 만약, Feature Store가 없다면 DE, DS, MLE 들은 서로의 정보를 구두로, 수작업으로 일일이 맞춰야하며 이로인해 휴먼 에러의 발생률이 높아질 수 있어요.

Feature Store는 단순히 Feature를 저장하는 창고 이상의 의미를 가집니다. 그것은 곧 “ML에서 데이터 품질과 일관성을 보장하는 데이터 기반의 소프트웨어 시스템”이며, Feature Store는 MLOps 아키텍처에서 아래와 같은 중심적인 역할을 수행합니다:

  * 학습과 서빙에 동일한 Feature를 안정적으로 제공하여 Training-Serving skew를 방지
  * 기존에 정의된 Feature를 재사용 가능하게 만들어 중복 구현을 줄이고 협업을 효율화
  * 실시간 Feature/Batch Feature 모두 지원하며, 실제 서비스 Latency 요구사항에 맞춘 운영이 가능
  * Feature 수준의 메타데이터, 품질 모니터링, 권한 관리 기능을 통해 안전하고 신뢰할 수 있는 ML 운영 환경을 제공

Feature Store Internal과 외부 컴포넌트 \(출처: <https://feast.dev/blog/what-is-a-feature-store/>\)

## Toss Feature Store

### 왜 Toss에 Feature Store가 필요한가요?

토스는 다양한 도메인에 걸쳐 수십 개의 ML 모델이 운영되고 있으며, 각 모델은 서로 다른 팀, 데이터 소스, 서빙 요구사항을 갖습니다. 모델 성능과 운영 효율성을 동시에 확보하기 위해서는 일관된 Feature 관리 체계와 강력한 재사용성, 안정적인 서빙 인프라가 필요했습니다. 이를 해결하기 위한 핵심 인프라가 Feature Store입니다.

  * ML 모델을 빠르게 개발하고 서빙 할 수 있게 된다. 

    * 기존엔 오프라인에서 Feature 생성 및 모델 학습을 하고, 모델마다 API 서버에서 Feature를 제공하도록 개발 해야했음
    * 위 방식은 개발 속도가 느림, 의도와 다른 Feature 생성으로 온라인에서의 모델의 성능이 떨어질 수 있음

  * 신규 프로젝트에서 기존에 생성된 Feature를 재사용 하여서 작업 속도를 향상 시킬 수 있다.

    * 잘 만들어지고 사용되는 Feature를 재사용 하지 못하고 새로운 프로젝트마다 Feature 생성부터 새롭게 개발해야 했음
    * 동일한 Feature를 중복으로 만들게되어 일관성이 저하되고 리소스 낭비가 있음

  * Feature Quality Monitoring

    * Feature 품질에 문제가 생겼을 때, ML 모델을 기반으로 서비스되는 부분에 결과 품질에 치명적인 영향을 줄수 있음
    * Feature Level로 Feature의 품질\(분포, Min-Max, Null Value의 크기 등\)에 문제가 생기는지 모니터링할 필요가 있음

  * 데이터 접근 및 권한 관리

    * 학습을 위한 데이터 접근 포인트를 단일화 하고, 그것에 대한 권한 관리를 함으로써 보안을 강화할 수 있음
    * ML 학습 특성상 대부분 모델 학습에 있어서 익명화된 데이터를 사용하는 것이 가능하며, Feature Store를 통해서 비교적 쉽게 익명화된 데이터를 ML모델 학습을 이루어지게 할 수 있음

### 왜 오픈소스를 안 쓰고 직접 개발하나요?

Feature Store는 단순한 툴이 아니라 ML 인프라의 중심축이기 때문에, 서비스 환경에 맞지 않으면 오히려 운영 부담이 커질 수 있습니다. 기존 오픈소스도 충분히 훌륭하지만, 다음과 같은 이유로 토스는 자체 구축을 선택했습니다. 그 과정에서 오픈소스인 [Feast](https://feast.dev/)의 개념과 구조를 많이 참고했어요.

  * 니즈에 딱 맞는 오픈소스의 부재

    * 주요 오픈소스: [Feast](https://feast.dev/), [Tecton](https://www.tecton.ai/), [Hopsworks](https://www.hopsworks.ai/)
    * 데이터 소스가 복잡하지 않고 단순함
    * 복잡한 회사의 니즈를 충족시켜 주지 못함

  * 오픈소스나 엔터프라이즈 버전을 사용할 때 비슷한 수준의 리소스가 필요할 것이라고 예상 됨
  * 자체 개발 시 최대한 현재 시스템을 유지하면서 최소한의 개발로 가능
  * ML에 있어서 가장 중요한 플랫폼으로 자체적으로 토스팀의 니즈에 맞게 지속적으로 개발 운영되어야 할 필요

### System Architecture

Feature Store는 크게 몇 가지 역할을 하는 컴포넌트로 묶을 수 있습니다. 먼저 사용자는 Feature를 학습 & 서빙에 사용하기 위해 다양한 Meta와 함께 Admin Dashboard와 SDK로 Feature를 등록합니다. 학습용 데이터가 저장되는 Offline Storage와 On-demand Feature 서빙을 위한 Online Storage와 Feature Serving API서버가 존재합니다. 또한 ML 모델학습에도 Feature Store의 정보들이 사용되는데, 이 과정에서 Trainkit이 사용됩니다. Trainkit은 학습에 핵심적인 역할을 하는 컴포넌트로 뒤에서 자세히 설명하겠습니다.

Online Storage로 Redis, ScyllaDB, Cassandra 등 다양한 선택지가 있습니다. 과거에 HBase, Redis등을 사용했었고, 현재 토스 Feature Store는 대용량 트래픽에 대해 Low Latency를 보장하는 고성능 Key-Value Storage인 [Aerospike](https://aerospike.com/) 클러스터를 Online Storage로 사용하고 있습니다. 저희 케이스에서는 다양한 도메인에서 생성한 Feature를 서빙하기 용이한 형태로 가공하여 배치 및 실시간으로 Aerospike에 Write가 필요합니다. Aerospike는 Key는 메모리에 올려 사용하고 Record의 경우 Disk에 저장하는 메모리 & SSD\(HDD\) 하이브리드 아키텍쳐를 제공합니다. Model Inference를 위한 Feature Serving 또한 설명할 내용이 많은데요. 추후 이부분에 대한 내용도 공유하도록 하겠습니다.

### Data Model

Feast의 Data Model을 참고하여 토스 내의 데이터 상황에 맞게 수정하여 사용하고 있습니다. 여기서 Feature Store가 단순히 Feature를 각 하나하나 씩 정의해서 사용하는 것이 아니라 Feature Table, Feature Service등 일종의 Feature Set 단위가 필요하다는 것을 볼 수 있어요.

Feature Table은 데이터와 밀접하게 연관되며, Hive Table등과 같이 물리적인 데이터 테이블을 Wrapping한 개념입니다. 테이블의 컬럼을 Entity, Feature, Partition로 구조화하여 Feature Store의 소스로 포함하게 됩니다. Feature Service는 학습과 서빙 시에 ML 모델과 밀접하게 관련이 있는 논리적인 단위입니다. 더 나아가서 Trainkit & Servingkit에서 까지 활용되는 중요한 단위가 돼요.

  * `Entity` : 학습데이터에서 Example을 나누는 키. Feature 테이블 생성시에 Entity는 정해져 있음. 테이블 내에서 유니크 함.
  * `Feature` : 테이블의 컬럼. Toss Feature Store에서 데이터를 관리하는 단위.
  * `FeatureTable` : Feature 사용을 위해서 오프라인\(Batch\)으로 생성된 테이블. Impala 테이블의 경우에 Entity, Features, Partition Column 등으로 구성된다. 이미 존재하는 Impala 테이블에 대한 명세이며, Metadata에 등록하여 테이블 간 조인 시 정보를 제공하도록 한다.
  * `FeatureService` : 최종적으로 ML모델 학습과 Inference에 사용되는 데이터 모델이다. FeatureTable의 리스트, Entity로 정의된다. 

<https://docs.feast.dev/getting-started/concepts/data-ingestion>

### Feature Store Admin

보안정책 등 컴플라이언스 이슈 및 사내의 요구사항을 반영하기 위해 자체 개발한 Feature Store Admin이 있습니다.

토스는 사내에 Data Center라는 도구가 있고, 테이블 형태의 데이터를 쉽고 빠르게 확인해 볼 수 있는데요. Data Quality 또한 지속적으로 관리되고 있습니다. Feature Store는 이 Data Center와 연동되어 Feature Store의 소스가 되는 Feature Table을 등록할 수 있습니다. 그 과정에서 테이블의 컬럼을 Entity, Feature, Partition로 구조화하여 Feature Store로 포함하게됩니다. 

Data Center와 연동되어 Feature Table을 등록하는 모습Feature Store의 소스가 되는 등록된 Feature Table들의 정보학습과 서빙시 중요한 단위로 사용되는 Feature Service

## Trainkit

모델 학습 파이프라인은 데이터 로딩 → 전처리 → 모델 학습 → 후처리 → 평가 단계로 표준화되어 있지만, 실제로는 “모델 학습” 단계를 제외한 나머지 부분이 팀 또는 프로젝트마다 제각각의 방식으로 구현되며 큰 비효율을 낳습니다. 예를 들어, 같은 데이터셋을 다루더라도 어떤 팀은 Impala SQL을 통해 데이터를 로딩하기도 하고, 어떤 팀은 HDFS에서 Parquet 파일을 직접 읽어 데이터를 가져오기도 합니다. 데이터 로딩하는 방법은 너무나도 많으니까요. 이런 표준화되지 않은 각각의 워크플로우들은 아래와 같은 많은 문제점들을 야기합니다.

  * 중복 코드: 데이터 로딩이나 반복되는 전처리 스크립트가 프로젝트마다 새로 작성되어, 작은 버그 수정조차 여러 곳에서 반복 작업을 해야 합니다.
  * 재현성 저하: 동일한 실험을 돌리더라도, 데이터 셔플링 방식이나 체크포인트 저장 로직이 서로 달라서 결과가 미묘하게 달라집니다. 이로 인해 ‘어제 성공했던 실험이 오늘은 왜 실패할까?’라는 질문이 잦아집니다.
  * 기술 부채: 신규 입사자는 각 프로젝트별로 설계된 파이프라인 구조를 이해하기가 어렵고 담당자 부재로 인한 유지보수가 어려워집니다.

이렇듯 학습 파이프라인의 비핵심 레이어가 팀별로 산발적으로 개발됨에 따라, 개발·유지보수 비용이 기하급수적으로 늘어나고, 협업 효율은 오히려 떨어집니다. “데이터 준비부터 실험 관리까지의 인터페이스를 명확히 정의하고 공유하면 모델러들은 모델 설계에만 집중할 수 있지 않을까”라는 생각에서 출발한 것이 바로 Trainkit의 탄생 배경입니다.

## Trainkit 구조

Trainkit은 Feature Store\(FS\)와 강하게 결합된 모듈입니다. 모든 Feature 메타 정보를 포함한 Feature의 Entity 정보를 FS에서 조회해 오기 때문에, FS는 Trainkit에 필수적인 컴포넌트입니다. Trainkit의 학습 구조는 크게 5가지 Data Module, Target, Feature Package, Feature Service, Feature Processor로 구분되어 있습니다.

1️⃣ Data Module

PyTorch Lightning의 LightningDataModule을 상속해 만든 커스텀 객체로, 전체 데이터 파이프라인\(데이터 로딩 → 전처리 → 배치 생성\)을 담당합니다. 내부에서 Feature Package를 활용해 실제 데이터를 가져오고 전처리까지 수행합니다.

2️⃣ Target

여러 Feature를 조인할 때 기준이 되는 데이터 스펙을 정의하는 컴포넌트입니다. 예로, 추천 시스템에서 Target은 실제 사용자의 반응을 가지고 있는 데이터셋입니다. 

3️⃣ Feature Service

Feature Store\(FS\) API와 연동되어있는 컴포넌트입니다. FS API를 통해 Feature 메타정보를 조회하고 FS가 가지고 있는 Entity 데이터를 읽어옵니다. 이 레이어는 실제 데이터 생성을 위한 쿼리를 만들어내는 곳이기도 합니다. Target의 데이터와 FS에서 찾은 Entity를 Join Key로 사용하여 여러 Feature들을 병합해주는 Join SQL을 생성해줍니다.

4️⃣ Feature Processor

각 Feature에 적용할 전처리 로직을 수행해주는 컴포넌트입니다. Casting, Imputation, Scaling, Encoding의 전처리가 들어가있으며 특정 Feature에 적용하고 싶은 전처리 로직을 명세해둔다면 자동으로 데이터 로딩과정에서 적용됩니다. 전처리 컴포넌트는 추상화가 잘 되어있어 Fit, Transform 함수만 정의해둔다면 쉽게 신규 전처리 로직을 추가할 수 있는 구조입니다.

5️⃣ Feature Package

Feature Service와 Feature Processor를 들고 있는 Facade Layer의 객체입니다. 이 레이어에서 데이터 로딩 속도를 위한 캐싱, Feature 유효성 검사, 데이터 로딩 API 등의 기능을 담당합니다.

위 구조를 가지고 Trainkit은 다음과 같은 워크플로우로 데이터셋이 생성되게 됩니다.

  1. Data Module 생성에 필요한 정보를 준비한다.
  2. Target을 토대로 조인의 기준이 되는 데이터를 가져오고 Feature Processor를 통해 전처리를 수행한다.
  3. n개의 Feature Package에서 Feature Service 정보를 토대로 Feature 정보를 가져오고 Feature Processor를 통해 전처리를 수행한다.
  4. Data Module에서 Train, Validation, Test용 Dataset, Dataloader를 생성한다.

이렇게 생성된 Dataloader를 사용하여 모델 학습을 진행할 수 있습니다.

## Trainkit이 해결하는 3가지 핵심 과제: 멀티 FeaturePack 조인, Train-Serving skew 해소, PIT 조인

위에서 Trainkit이 학습 파이프라인을 정형화하면서 가져온 구조적 장점들에 대해서 말씀드렸습니다. 사실 Trainkit은 구조적 장점뿐만 아니라 여러가지 Key Feature들을 제공하고 있습니다. 그 중 가장 많이 사용되고 있는 3가지 기능에 대해 말씀드릴게요.

### 1\. 멀티 Feature Package 조인으로 복잡한 Feature 결합 간소화

토스에서는 추천 모델의 Feature 카테고리를 크게 Feedback, User, Item으로 나누고 있습니다. Feedback은 반응 데이터, User는 유저 관련 Feature, Item은 상품 데이터를 의미합니다. 광고 소재 추천을 예로 든다면 Feedback은 유저의 Click여부, User는 유저 Feature, Item은 광고 소재 Feature가 됩니다. 이렇게 나뉜 Feature 카테고리를 데이터 소스 구조에도 동일하게 녹여낸다면 확장성에 큰 제한을 받게 됩니다. 이를 해결하기 위해서 Trainkit에서는 Target 이라는 하나의 데이터 셋을 기준으로 무한한 FeaturePack을 결합할 수 있는 구조로 만들었고, 이로인해 모델러들은 복잡한 Feature를 보다 간결하고 효율적으로 결합할 수 있게 되었습니다. 

Feature Store에 토스 내에서 활용할 수 있는 유저 프로파일, 유저 행동이력, 쇼핑 상품 카탈로그, 쇼핑 상품 메타 정보가 등록되어 있다고 가정해 보겠습니다. 기존에는 4개의 나누어져 있는 데이터셋을 재가공하여 Feedback, User, Item의 3가지 데이터 셋으로 재분류 해줘야했던 반면, Trainkit을 사용하면 단순히 사용하고 싶은 Feature Service를 지정해 주기만 하면 됩니다. Trainkit 내부에서 Feature Store에 등록된 메타 데이터를 기반으로 Join Key를 생성하고 결과를 얻을 수 있는 SQL과 함께 데이터를 손쉽게 얻을 수 있습니다. 이로인해 다른 누군가가 이미 생성해둔 사용하고 싶은 Feature가 있다면 언제든지 가져다가 학습 데이터로 사용할 수 있는 구조로 발전했습니다.

### 2\. Training-Serving Skew 해소

오프라인 학습과 온라인 서빙의 Feature skew를 맞추는 일은 매우 중요하면서도 까다롭습니다. 학습과 온라인 서빙시 사용된 Feature 값이 서로 다른 시점의 데이터를 보고있다면 모델이 잘못된 성능 지표를 내고 예측 성능이 하락하게 되는 Training-Serving Skew 현상이 발생합니다. 예를 들어, 온라인 서빙에서는 ‘현재 시각 기준 2시간 전’까지의 Feature만 사용하지만, 학습 시에는 ‘1시간 전’ 데이터까지 포함했다면 미래 정보가 학습에 유입되어 데이터 누수\(Data Leakage\)가 발생합니다. 이로 인해 오프라인 실험 결과와 온라인 서비스 성능이 크게 달라질 수 있습니다. 개개인이 Feature Store에 등록하는 Feature에서 시간 파티션의 해석이 다를 때도 문제가 발생할 수 있습니다. 00시 - 01시 사이에 발생한 데이터를 00시 파티션에 넣을 수도, 01시 파티션에 넣을 수도 있기 때문에 Target과 Feature의 파티션이 달라 조인이 어려워질 수도 있습니다.

Trainkit에서는 이를 해결하기 위해 학습 데이터를 생성할 때 시간 기준을 Shift 시켜줄 수 있는 기능을 구현했습니다. Target 데이터를 기준으로 시간 파티션을 Shift 할 수 있어요. 예를들어, 01시에 발생한 피드백 데이터라도 Shift 기능을 사용하여 00시에 발생한 Feature들과 조인하여 데이터 누수를 방지할 수 있습니다. 

기존에는 Skew를 해결하기 위해 Feature를 재생성 해야하거나 데이터 누수를 발견하더라도 대응하는데 시간이 오래 걸렸던 반면, Shift 기능을 사용하여 설정 변경 하나로 바로 문제 해결이 가능해졌습니다.

### 3\. PIT \(Point-In-Time\) 조인으로 정확한 Feature 생성

모델 온라인 서빙을 할 때 Feature들의 PIT Join은 필수적인 기능입니다. 온라인 서빙 시점에서 Feature의 값은 지속적으로 변화하고 변화된 Feature를 기준으로 추론했을 때의 반응을 기록하게 됩니다. 이 데이터를 다시 오프라인 학습에서 사용해야하는데 Feature들이 시간 의존성을 가지고 있기 때문에 적절한 Feature 값을 찾아 반응 데이터와 병합해 줘야합니다.

출처: <https://docs.databricks.com/aws/en/machine-learning/feature-store/time-series>

특정 시점에 발생했던 가장 최근 Feature들을 찾아 병합해야 오프라인/온라인 데이터 일관성을 유지할 수 있습니다.

하지만 PIT join은 구현하기도 까다롭고 비용도 많이드는 작업입니다. Trainkit에서는 PIT를 적은 메모리로 처리하기 위해 런타임에서 join을 실행합니다.

데이터셋 객체는 Target과 Feature Package 정보를 기반으로 생성됩니다. 객체를 생성하는 시점에는 PIT 조인을 하지않고 이를 위한 준비만 진행합니다. Target으로 PIT에 필요한 join key를 생성하고, 각각의 Feature Package와 맵핑된 딕셔너리를 만들어 조인을 위한 준비를 완료합니다. 

Data Module에서 필요한 index의 데이터셋을 호출할 때 조인이 수행됩니다. Target에서 index를 기준으로 join key를 찾아내고, join key에 해당하는 Feature들을 준비과정에서 만들어둔 딕셔너리에서 조회하여 가져옵니다. 각 Feature Package에서 가져온 Feature들을 Concatenate하여 결과적으로 join key를 기준으로 결합된 Feature 리스트를 반환하게 됩니다.

만약 미리 join을 시켜놓고 런타임에는 index 조회만하여 가져오면 어떻게 될까요? 
    
    
    #Target data
    [(user_pack_1, item_pack_1), 
     (user_pack_1, item_pack_1), 
     (user_pack_1, item_pack_2), 
     (user_pack_2, item_pack_1), 
     (user_pack_2, item_pack_2), 
     (user_pack_2, item_pack_2)]

로 6개의 타겟 데이터가 있고 각각의 pack안에는 6개의 Feature가 있다고 가정해 보겠습니다. user_pack_1, user_pack_2, item_pack_1, item_pack_2 모두 각각 3번이 반복됩니다. 

  * 미리 join 할 경우

    * target 6 + User Feature 6 * 3 + Item Feature 6 * 3 = 42

  * 런타임 join 하는 경우

    * target 6 + 3 + 3 = 12

Feature Package 및 Feature의 개수가 늘어날수록 미리 조인을 해놓을 경우 메모리 점유율은 기하급수적으로 늘어나기 때문에 런타임에서 조인하는 방향으로 해결했어요.

위 3가지 핵심 기능 이외에도 학습 파이프라인을 플랫폼화 하기위해 많은 기능들이 제공되고 있으며, 학습 뿐만 아니라 ServingKit을 사용한 학습 → 서빙까지의 일원화를 위한 플랫폼화를 진행하고 있습니다.

### 마무리

지금까지 Feature 관리부터 학습까지의 일련의 과정을 Feature Store와 Trainkit을 사용했을 때 어떤 이점을 챙길 수 있는지에 대해 설명드렸어요. ML Platform 팀에서는 이 뿐만 아니라 Model Registry, Inference System, Monitoring System 등 데이터 준비부터 학습, 서빙, 배포, 모니터링까지 일련의 End-to-End 파이프라인을 플랫폼화하는데 노력하고 있습니다. 효율적이고 확장 가능한 ML 플랫폼에 관심이 있는 분이라면 언제든지 환영이니 많은 지원 부탁드립니다.