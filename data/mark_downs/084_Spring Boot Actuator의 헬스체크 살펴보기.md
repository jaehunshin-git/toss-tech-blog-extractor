# Spring Boot Actuator의 헬스체크 살펴보기

**Date:** 2023년 4월 1일
**URL:** https://toss.tech/article/how-to-work-health-check-in-spring-boot-actuator

---

뭐든 알고 쓰는 게 참 중요한 것 같습니다. 단순히 “지금은 잘 돌아가니까 문제 없다”는 접근은 문제가 발생하기 전까지는 문제를 방치하기 마련입니다.

사용하는 기술이나 구조에 대해 끊임없이 질문을 던지고 탐구하는 과정은 [토스팀 코어밸류 3.0](https://blog.toss.im/article/core-values-are-evolving) 중 하나인 Question Every Assumption, 모든 기본 가정에 근원적 물음을 제기한다에도 부합하는 사례인것 같습니다. 이번 포스트에서는 제가 개발 과정에서 헬스 체크를 별다른 생각 없이 [Spring Boot Actuator](https://docs.spring.io/spring-boot/docs/3.0.5/reference/html/actuator.html)가 제공하는 기능을 사용하면서 겪은 이슈를 간략하게 설명해보겠습니다.

## 들어가기에 앞서

이 포스트는 작성 시점 기준에서 최신 Spring Boot GA\(General Availability\) 버전인 3.0.5 버전을 기준으로 설명합니다. 해당 버전의 하위/상위 버전에서는 기능이 미묘하게 다르게 동작할 수 있습니다. 2.x 버전에서도 큰 맥락에서는 동일한 동작을 보장하리라 추측되지만 본인이 사용하는 버전에 해당하는 자세한 내용을 찾아보시길 권장합니다.

## 헬스 체크란?

서비스의 고가용성\(HA, High Availability\), 고성능을 위한 부하 분산 등의 이유로 우리는 서버의 이중화\(혹은 그 이상\)를 하고, 앞에서 어떤 서버로 요청을 보낼지 라우팅 역할을 하는 로드 밸런서를 둡니다.

로드 밸런서가 적절히 부하를 분산하여 A/B 서버 중 한 대에게 클라이언트의 요청을 보냅니다.

하지만 아래와 같이 서버 한 대가 서비스 불가 상태라면 어떻게 해야할까요? 해당 서버에 요청이 들어가야할까요?

혹은 대량의 트래픽이 들어올 것을 대비하는 등등의 이유로 서버를 증설해야 하는데 해당 서버가 관련된 소스코드를 로딩하고 있다면 어떻게 해야할까요? 이 때도 마찬가지로 해당 서버에 요청이 들어가야할까요?

두 케이스 모두 해당 서버로 요청을 보내면 안 됩니다. 정상적인 서비스가 불가능해서 클라이언트의 요청을 수행할 수 없습니다. 장애를 유발하거나 해당 서버의 부하를 크게 증가시켜 오히려 장애를 더 심각하게 만들 수도 있습니다.

따라서 로드 밸런서에서는 각 서버의 헬스 체크 API를 호출해서 해당 서버가 현재 서비스 가능한 상태인지 아닌지 주기적으로 점검합니다.

헬스 체크 API 경로는 커스텀하게 설정 가능합니다.

헬스 체크에서 서버에 문제가 발견되면 로드 밸런서는 해당 서버로 요청을 보내지 않게 됩니다.

헬스 체크는 정상적으로 서비스가 가능한 서버에만 트래픽을 보내서 서비스의 고가용성을 확보하는 데 도움됩니다.

## Spring Boot Actuator의 헬스 체크

[Spring Boot Acutator](https://docs.spring.io/spring-boot/docs/3.0.5/reference/html/actuator.html)를 의존성으로 추가하면 기본적으로 헬스 체크 엔드포인트가 활성화됩니다.

Spring Boot 3.x 기준으로 헬스 체크 엔드포인트는 `/actuator/health`이고, 설정을 바꾸지 않아도 해당 엔드포인트로 접속하면 HTTP 200 상태 코드와 해당 서버의 상태가 Response Body로 응답됩니다.

크롬 개발자 도구로 확인해본 Spring Boot Actuator의 헬스 체크 결과

Spring Boot Actuator는 어떠 기준으로 서버의 헬스 체크를 할까요? 확인하려면 [Health Information 문서](https://docs.spring.io/spring-boot/docs/3.0.5/reference/html/actuator.html#actuator.endpoints.health)를 살펴보면 됩니다. 해당 정보는 보안에 민감한 요소가 들어있을 수 있어서 퍼블릭하게 접근이 가능해서는 안 됩니다. 저는 로컬에서 간단하게 확인만 해보는 목적으로 `application.yml(application.properties)` 파일에 `management.endpoint.health.show-details: always`로 설정한 후에 다시 헬스 체크 결과를 확인했습니다.

[Auto-configured HealthIndicators](https://docs.spring.io/spring-boot/docs/3.0.5/reference/html/actuator.html#actuator.endpoints.health.auto-configured-health-indicators)\([WebMVC](https://docs.spring.io/spring-framework/docs/6.0.7/reference/html/web.html#mvc) 전용\)와 [Auto-configured ReactiveHealthIndicators](https://docs.spring.io/spring-boot/docs/3.0.5/reference/html/actuator.html#actuator.endpoints.health.auto-configured-reactive-health-indicators)\([Webflux](https://docs.spring.io/spring-framework/docs/6.0.7/reference/html/web-reactive.html#spring-webflux) 전용\)에 나열된 [HealthIndicator](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/health/HealthIndicator.java)\(혹은 [ReactiveHealthIndicator](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/health/ReactiveHealthIndicator.java)\)는 [Spring Boot Auto Configuration](https://docs.spring.io/spring-boot/docs/3.0.5/reference/html/using.html#using.auto-configuration)에 의해 자동으로 활성화되는데 관련된 의존성이 존재할 때만 활성화 되는 것들도 있습니다. 예를 들어, [DataSourceHealthIndicator](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/jdbc/DataSourceHealthIndicator.java)는 [DataSourceHealthContributorAutoConfiguration](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator-autoconfigure/src/main/java/org/springframework/boot/actuate/autoconfigure/jdbc/DataSourceHealthContributorAutoConfiguration.java)에 의해 설정되는데 [Spring Data JPA](https://docs.spring.io/spring-data/jpa/docs/current/reference/html/) 같이 DataSource를 사용하는 의존성을 추가했을 때 활성화됩니다.

그럼 코드레벨에서 각 `(Reactive)HealthIndicator`들이 어떻게 사용되는지 보겠습니다.

먼저 `/actuator/health`에 접속한 뒤에 브레이크 포인트를 걸고 디버그 모드로 살펴보면 [HealthEndpointSupport 클래스의 getAggregateContribution 메서드](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/health/HealthEndpointSupport.java#L155-L161)에서 각 [HealthContributor](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/health/HealthContributor.java)\(혹은 [ReactiveHealthContributor](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/health/ReactiveHealthContributor.java)\)를 순회하면서 [헬스 체크하는 코드](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/health/HealthEndpointWebExtension.java#L92-L95)를 보실 수 있습니다. \(헬스 체크하는 코드에 있는 HealthIndicator 인터페이스는 HealthContributor 인터페이스를 상속받았습니다.\)

[HealthEndpointSupport 클래스의 getCompositeHealth 메서드](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/health/HealthEndpointSupport.java#L193-L202)에서는 각 HealthIndicator로부터 수집한 상태를 바탕으로 현재 서버의 상태를 진단합니다.
    
    
    @Override
    public Status getAggregateStatus(Set<Status> statuses) {
        return statuses.stream().filter(this::contains).min(this.comparator).orElse(Status.UNKNOWN);
    }
    
    
    /**
     * {@link Comparator} used to order {@link Status}.
     */
    private class StatusComparator implements Comparator<Status> {
    
        @Override
        public int compare(Status s1, Status s2) {
            List<String> order = SimpleStatusAggregator.this.order;
            int i1 = order.indexOf(getUniformCode(s1.getCode()));
            int i2 = order.indexOf(getUniformCode(s2.getCode()));
            return (i1 < i2) ? -1 : (i1 != i2) ? 1 : s1.getCode().compareTo(s2.getCode());
        }
    
    }

[SimpleStatusAggregator의 getAggregateStatus 메서드](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/health/SimpleStatusAggregator.java#L73-L76)에서는 각 상태를 수집해서 하나의 Status로 반환하고 있는데 이 때 [StatusComparator](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/health/SimpleStatusAggregator.java#L100-L113)가 사용됩니다.
    
    
    defaultOrder.add(Status.DOWN.getCode());
    defaultOrder.add(Status.OUT_OF_SERVICE.getCode());
    defaultOrder.add(Status.UP.getCode());
    defaultOrder.add(Status.UNKNOWN.getCode());
    DEFAULT_ORDER = Collections.unmodifiableList(getUniformCodes(defaultOrder.stream()));

이 때 가장 중요한 것은 Status의 순서인데 [SimpleStatusAggragtor의 static 생성자 블럭](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/health/SimpleStatusAggregator.java#L42-L50)을 보게되면 위와 같은 순서로 추가하고 있고,
    
    
    public SimpleStatusAggregator() {
        this.order = DEFAULT_ORDER;
    }

별도의 순서를 주지 않은 [기본 생성자](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/health/SimpleStatusAggregator.java#L56-L58)는 `defaultOrder`에 추가한 순서를 사용하는 것을 볼 수 있습니다.

`getAggregateStatus`는 `Status` 중에 가장 순서가 빠른\(오름차순\) 것 하나를 반환하게 되어있기 때문에 만약에 `Down`을 반환한 `HealthIndicator`가 하나라도 존재하면 서비스의 상태를 `Down`으로 생각해서 `503`을 반환하게 됩니다.

## 헬스 체크에서 조심해야 하는 점

Spring Boot Actuator 헬스 체크의 동작원리를 잘 모르고 사용하면 일어날 수 있는 문제를 설명하겠습니다.

### 1\. 의도치 않은 장애 발생

각 서버에서는 서비스를 제공하는 서비스 DB와 데이터를 분석하는 로그 DB가 있다고 가정하겠습니다. 그리고 로그 DB에 적재하는 작업은 비동기로 별도의 스레드에서 처리하도록 작업을 해놨다고 가정하겠습니다. 로그 데이터 저장이 불가능하더라도 실시간 서비스에는 문제가 없도록 하기 위해서죠.

이 때 만약 로그 DB에 작업을 해야해서 순단이 발생하거나 접속에 문제가 생긴다면 어떻게 될까요? 아래 정답을 확인하기 전에 1분 동안 한 번 생각해보시길 바랍니다.

위에 Spring Boot Actuator의 헬스 체크는 여러 `HealthIndicator`가 수집한 상태를 토대로 서비스의 상태를 판단한다고 말씀드렸습니다. 그 순서를 차근차근 설명해보겠습니다.

  1. `RoutingDataSourceHealthContributor`에 의해 여러 DataSource의 헬스를 체크합니다.

     1. `DataSourceHealthIndicator`에 의해 서비스 DB의 상태를 체크했을 때는 `UP`이 반환됩니다.
     2. `DataSourceHealthIndicator`에 의해 로그 DB의 상태를 체크했을 때는 `DOWN`이 반환됩니다.

  2. 수집한 상태들은 `SimpleStatusAggregator`에 의해 서비스 상태를 판단하게 되는데 아무런 순서 설정을 하지 않았으면 DOWN인 게 하나라도 있다면 `DOWN`이 반환됩니다.
  3. 서비스의 상태가 `DOWN`\(`503`\)으로 판단됐기 때문에 로드 밸런서에서는 서버로 트래픽을 보내지 않게 됩니다.
  4. 서비스 DB에 문제가 없음에도 불구하고 클라이언트의 요청은 처리되지 않고 장애가 발생합니다.

우리는 분명 최대한 높은 가용성을 보장하기 위해 로그 DB의 장애가 전파되지 않도록 격리했음에도 불구하고 장애가 발생할 수 있습니다. 이를 해결하기 위해서는 아래와 같은 방법 등등이 있습니다.

  * Spring Boot Actuator의 헬스 체크가 아닌 직접 헬스 체크 API를 구현할 수도 있습니다.
  * `HealthIndicator` 중에 헬스 체크에 영향을 끼치지 않길 희망하는 것들은 비활성화 시키는 방법도 있습니다. \(RDB를 예로 들자면 `management.health.db.enabled: false`\(기본값 `true`\)로 설정한다거나\)
  * 문제가 되는 `HealthIndicator` 빈을 직접 생성해서 Auto Configuration의 동작을 오버라이딩 하는 방법 등등이 있습니다.

다만 헬스 체크에 이런 저런 로직들이 들어간다는 것은 일반적으로 예측 가능하지 못할 수 있으므로 팀 내에 꼭 공유가 잘 되어야할 것입니다.

### 2\. 트러블 슈팅의 지연

> 비슷한 상황으로, 예전에 API 서버에서 외부 의존성 중에 ES만 죽었는데, API 서버가 죽었다고 판단돼서 DOWN이 된적이 있었어요. 헬스 체크에서 detail 옵션을 키면, 상세하게 쭉 나오더라고요. 당시에 LB 통해서 접근이 안 됐는데, WAS는 개별로 접근했을 때는 문제가 없어 보여서 트러블 슈팅이 늦어졌었습니다.

이는 실제 사내에서 비슷한 상황이 발생했을 때 트러블 슈팅이 지연된 사례입니다. Spring Boot Actuator 헬스체크의 동작원리를 정확히 이해했다면 ES\(Elasticsearch\) 서버가 죽었을 때 해당 서버의 헬스체크도 같이 죽게 된다는 걸 예측할 수 있습니다. \([ElasticsearchRestClientHealthIndicator](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/elasticsearch/ElasticsearchRestClientHealthIndicator.java) 혹은 [ElasticsearchReactiveHealthIndicator](https://github.com/spring-projects/spring-boot/blob/v3.0.5/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/data/elasticsearch/ElasticsearchReactiveHealthIndicator.java)가 ES 서버의 헬스체크를 해서 헬스체크 API 응답에 전체적으로 영향을 끼치기 때문에\)

하지만 헬스체크의 동작원리를 잘 모르면 우리가 장애를 격리했다고 생각한 시스템\(위의 상황에서는 ES\)에만 문제가 있는데 왜 장애가 발생하는지, 왜 도메인을 통해서 접근하면 접근이 안 되는지 상황 파악이 안 될 수 있습니다. 서버는 정상적으로 살아있고 부하도 없는 상황이라면 헬스 체크 API를 호출할 생각도 못 하고, 로드 밸런서의 버그인지부터 의심을 할 수도 있습니다. 이렇게 엉뚱한 포인트를 의심하게 되면 장애 상황은 계속 되고, 서버를 재시작해도 근본적인 문제를 해결\(위 상황에서는 ES 서버의 복구\)하기 전까지는 여전히 헬스 체크에 실패할테니 장시간 장애가 지속될 수도 있습니다.

결국 각 서버 인스턴스마다 직접 헬스 체크 API를 호출해서 정상 응답을 받는지 확인해봐야하는데 여기까지 사고의 흐름이 다다르는데 너무 많은 시간 소요와 불필요한 리소스 낭비들을 초래하게 됩니다.

## 마치며

평상시에는 헬스 체크하면 그냥 `200 OK`만 응답하는 정말 심플한 API 수준으로만 생각하고 큰 신경도 쓰지 않았습니다. 근데 사소한 것에 한 번 데인 뒤로부터는 개발자가 왜 호기심이 많아야하는지 한 번 더 깨닫게 되었습니다. 그냥 단순히 돌아만가는 코드가 아닌 이 코드가 왜 그렇게 돌아가는지, 우리가 왜 이 기술을 선택하게 된 것인지, 끊임없이 고민하고 탐구하기 위해서는 강력한 호기심이 동기부여가 되기 때문입니다. 이러한 고민을 미리했다면 장애 상황을 미연에 방지할 수 있고, 장애 발생 이후에라도 이슈 분석을 통해 트러블 슈팅 능력도 크게 향상된다는 것을 다시 한번 깨닫게 되는 소중한 경험이었습니다.

## 참고 링크

  * [Spring Boot Actuator Docs](https://docs.spring.io/spring-boot/docs/3.0.5/reference/html/actuator.html#actuator)
  * [NHN Forward spring-boot-actuator documentation](http://forward.nhnent.com/hands-on-labs/java.spring-boot-actuator/06-health.html)