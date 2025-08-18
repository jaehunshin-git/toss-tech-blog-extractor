# 에러 0%, MSA에서의 Enum 관리 전략

**Date:** 2025년 6월 18일
**URL:** https://toss.tech/article/msa-enum

---

안녕하세요, 토스뱅크 Server Developer 김인회 · 이준영입니다.

토스뱅크는 다른 은행과 달리 시스템을 MSA\(Microservice Architecture\)로 구축해 빠른 개발과 배포 속도를 누리고 있습니다. 하지만 "은탄환은 없다"는 말처럼, MSA는 다양한 복잡함을 수반했는데요. 그중 하나가 바로 Enum입니다.

이번 글에서는 MSA 환경에서 Enum이 왜 문제가 될 수 있는지, 그리고 토스뱅크는 이를 어떻게 해결했는지에 대해 소개해 드리려고 합니다.

## MSA에서는 독이 될 수 있는 Enum

Enum은 타입 안정성, 컴파일 타임 체크, IDE의 자동완성 등의 장점이 있어서 Java 혹은 Kotlin을 다뤄본 개발자라면 자주 사용하는 도구일 것 입니다.

하지만 MSA환경에서는 이러한 Enum이 자칫 독이 될 수도 있는데요.

MSA에서는 하나의 Enum을 각 서버끼리 공유할 때 정의되지 않은 Enum 값이 넘어오면 Deserialize 에러가 발생합니다.

Enum을 A, B 서버에서 공유하고 있을때 B서버의 버전이 A서버의 버전을 따라가지 못하면 에러가 발생합니다.

많게는 1년에 한두번씩 꾸준히 발생하는 이 문제는, 단순히 휴먼 에러라고 치부하기에는 너무 빈번하고 치명적이에요. 담당자가 바뀌거나, 서비스가 확장되거나, 새로운 Enum 값이 추가되는 순간 다시 문제가 발생하기 시작했고 토스뱅크 또한 예외는 아니었습니다. 

발전하는 MSA 속에서 Enum 관리가 점점 어려워지기 시작했고 결국 사람의 주의가 아닌 시스템적으로 이 문제를 예방하고 관리할 수 있는 방법이 필요해지기 시작했습니다.

## 제공자와 소비자

MSA에서 Enum 문제가 복잡해지는 이유 중 하나는 통신 주체에 따라 기대하는 동작이 다르기 때문입니다. 

그래서 저희는 요청 주체 기준으로 Enum 사용을 '제공자'와 '소비자'로 나누었고 각각의 Use Case에 맞는 전략을 수립했습니다.

1\. 클라이언트\(소비자\) → 서버\(제공자\): 요청을 수신하는 입장에서는 오류가 명확해야 한다.

클라이언트가 Enum 값을 요청으로 전달하고, 서버가 이를 파싱해 처리하는 구조에서 서버는 Enum 값의 의미를 정확히 이해하고 처리해야 하므로, 정의되지 않은 값을 받을 경우 즉시 에러를 반환하는 것이 타당합니다. 

예를 들어 `"UNKNOWN"`으로 처리해 흐름을 이어가면, 의도하지 않은 상태로 비즈니스 로직이 흘러갈 수 있고, 데이터 무결성이 훼손될 우려가 있습니다.

따라서 이 경우에는 Enum 값을 엄격하게 검증하고, 알 수 없는 값은 `400 Bad Request` 등의 클라이언트 오류로 응답하는 것이 바람직합니다.

2\. 서버\(제공자\) → 클라이언트\(소비자\) : 처리는 소비자의 선택에 맡긴다

반대로 서버가 Enum 값을 응답으로 보내고, 클라이언트가 이를 파싱하는 구조에서는 상황이 달라집니다. 서버가 Enum을 확장하여 새로운 값을 보내더라도, 클라이언트는 그 값을 아직 모를 수 있어요. 이때는 클라이언트 쪽에서 어떻게 대응할지를 선택할 수 있어야 합니다. 

예를 들어,

  * 알 수 없는 값이면 경고를 띄우고 무시한다
  * fallback 동작으로 `"UNKNOWN"` 또는 `"기타"`로 처리한다
  * 오류를 발생시켜 사용자에게 명시적으로 알린다

이처럼 소비자가 상황에 맞게 처리 전략을 선택할 수 있도록 열려 있는 구조가 필요합니다.

Kafka 소비자나 이벤트 핸들러 등 외부로부터 Enum을 수신하는 구조에서도 마찬가지입니다. 

이렇게, 각 Use Case 별 전략 수립 과정을 거쳐서 저희는 Enum deserialize 오류로부터 자유로워질 수 있는 아래 세 가지 해결책을 도출했습니다.

  1. Enum을 선택적으로 deserialize하기 - EnumString
  2. EnumString 전파하기 - ArchUnit
  3. Enum 배포 의존성 끊기 - Meta Expose

이번 글에서는 이 세 가지 해결책을 통해 어떻게 Enum deserialize 오류를 극복했는지 자세히 살펴보겠습니다.

## 1\. Enum을 선택적으로 deserialize하기 - EnumString

알지 못하는 Enum 값이 들어왔을 때 이를 역직렬화\(deserialize\)하는 방안을 고민하며, 처음에는 다음과 같은 방법들을 떠올렸어요.

  1. `@JsonEnumDefaultValue` 혹은 `@JsonCreator` 설정을 추가해서 입력과 일치하는 Enum이 없으면 기본값을 내려준다.
  2. `@JsonCreator`와 `Property` 를 사용해서 기본값을 반환할 Enum을 선택할 수 있게 한다.

하지만 이러한 해결법들은 기본값을 내려주더라도 도메인 로직상 여전히 예기치 않은 버그가 발생할 수 있으며, 개발자가 의도한대로 동작을 완전히 제어하기 어렵다는 한계가 있었습니다.

따라서 저희는 Enum 타입이 지닌 장점을 유지하면서도, 예상치 못한 값이 들어왔을 때 개발자가 직접 원하는 동작을 정의할 수 있는 유연한 접근법을 도입하기로 결정했어요.

하지만, 단순히 `String`으로 처리하는 것으로는 이 같은 유연성을 만족시키기 어렵고 사용성에 제한을 두기도 어려웠기 때문에, 아래와 같은 사용성을 제공하는 전용 라이브러리를 제작하게 되었습니다.

EnumString을 사용하는경우 Enum이 역직렬화 되는 과정

EnumString의 사용 예시를 코드로 보면 아래와 같은데요. 만약, EnumString이 아래와 같이 되어 있다고 가정하면,
    
    
    abstract class EnumString<E : Enum<E>, T : EnumString<E, T>>(
        @get:JsonValue
        override val value: String,
    ) : DelegatedValue<String>(value), Comparable<EnumString<E, T>> {
    
        
        
        open funtoEnumOrElse(defaultValueSupplier: () -> E): E =toEnumOrNull() ?: defaultValueSupplier()
        
        open fun toEnumOrThrow(exceptionSupplier: () -> RuntimeException = { IllegalStateException("\"$value\" 에 해당하는 ${EnumName}을 찾을 수 없습니다. dependency version을 체크해주세요.") }): E =toEnumOrNull()
            ?: throw exceptionSupplier()
            
        open fun toEnumOrNull(): E? = EnumFinder.findByNameOrNull(value)
        
        companion object {
            val CONSTRUCTOR_CACHE = ConcurrentHashMap<KClass<out EnumString<*, *>>, KCallable<*>>()
            inline fun <E : Enum<E>, reified T : EnumString<E, T>> E.toEnumString(): T {
                val constructor = CONSTRUCTOR_CACHE.computeIfAbsent(T::class) {
                    ...
                }
                return constructor.call(this.name) as T
            }
        }
    }

EnumString을 적용하려는 Enum은 아래처럼 간단히 `EnumString` 인터페이스만 구현하면 됩니다.
    
    
    Enum class Animal {
    
    	DOG,
    	CAT,
    	RABBIT,
    	;	
    }
    
    class AnimalString private constructor(
    	override valvalue: String
    ) : EnumString<Animal>(...)

이렇게 정의된 다음에는, DTO에서 Enum을 EnumString 타입으로 선언하고 나서 필요에 따라 선택적으로 역직렬화 결과를 처리할 수 있게 되는데요. 
    
    
    data class Foo(
     val animal: AnimalString,
    )
    
    // 아래와 같이 선택적으로 Enum을 deserialize 할 수 있습니다. 
    fun helloWorld() {
    	foo.animal.toEnumOrElse { throw IllegalArgumentException("역직렬화에 실패했어요.") }
    	
    	foo.animal.toEnumOrElse { return@toEnumOrElse Animal.DOG }
    	
    	// 혹은 필요에 따라 아래와 같은 편의 제공 메소드를 활용할 수도 있습니다.
    	foo.animal.toEnumOrThrow()
    	foo.animal.toEnumOrNull()
    }

사용자는 상황에 따라 세 가지 메소드를 유연하게 선택해 사용할 수 있습니다.

  * toEnumOrNull / toEnumOrElse: 무시해도 괜찮은 경우에는 `null` 또는 지정된 기본값을 반환하고,
  * toEnumOrThrow: 무시하면 안 되고 반드시 함께 버전업 되어야 하는 경우에는 예외를 발생시킵니다.

이처럼 `EnumString`을 도입하면서 불명확한 Enum 입력에 대해 “예외 발생” 또는 “기본값 할당” 등 원하는 동작을 직접 정의할 수 있게 되었고, 결과적으로 Deserialize 과정에서 발생할 수 있는 오류를 안전하게 제어할 수 있게 되었습니다.

## 2\. EnumString 전파하기 - ArchUnit

아무리 좋은 해결책 이더라도, 전파되지 않으면 무용지물이죠. 특히, 새로 합류한 구성원이 과거 문제를 잘 모른 채 기존처럼 Enum을 사용할 가능성도 고려해야 했어요. 그래서, 저희는 제공자 → 소비자 패턴에서 EnumString 사용을 시스템적으로 강제할 수 있는 방법을 찾기 시작했고 그 결과 ArchUnit을 찾게 되었습니다.

[ArchUnit](https://www.archunit.org/)은, 패키지와 클래스간의 의존성을 테스트 해주는 오픈소스 라이브러리 도구로 저희만의 커스텀 룰을 만들어서 제공하면 제공자 → 소비자 패턴에서 EnumString을 막을 수 있었습니다.

그래서 저희는 공용 레포에 대해 ArchUnit으로 규칙을 만들고, 컨슈머 코드에서 Enum 사용을 감지해 빌드 시점에 실패하도록 설정했습니다. 덕분에 새로운 구성원도 `EnumString`을 자연스럽게 사용하게 만들 수 있었습니다.

ArchUnit CI 실패 하는 사진

## 3\. Enum 배포의존성 끊기 - Meta Expose

위에서 소개한 EnumString 도입 이후, 서비스는 이전보다 훨씬 안정적으로 운영될 수 있게 되었습니다. 특히 버전과 무관하게 무시 가능한 Enum 값들에 대해서는 문제가 거의 발생하지 않게 되었죠.

하지만, 모든 Enum이 그렇게 유연할 수는 없었습니다. 어떤 Enum은 반드시 서비스 간에 함께 버전업이 되어야만 의미가 유지되며, 그렇지 않으면 여전히 오류가 발생할 수 있습니다.

예를 들어, 소비자\(Consumer\)라고 하더라도 "정의되지 않은 Enum 값을 받으면 도메인 로직이 깨지므로 오류를 발생시켜야 하는" 경우도 있었고, 제공자\(Publisher\) 입장에서도 Enum이 갱신되지 않은 소비자에게 메시지를 전송하면 실패가 발생하는 구조는 여전히 유효했습니다.

이를 해결하기 위해 저희는 Enum의 버전 동기화 상태를 관찰\(Observe\)하고 감지할 수 있는 시스템, `Meta-Expose`를 설계하고 도입하게 되었습니다.

### Meta Expose의 핵심 구성과 동작 방식

Meta Expose의 구조를 그려보면 아래와 같은데요. 중앙의 Meta-Expose-Hub에서 Enum을 사용하는 모든 서버를 watch하고 있다가 버전이 올라가지 않은 서버를 자동으로 감지해 어드민과 모니터링 도구로 알림을 주게 됩니다.

  * 자동 노출된 Enum API

    * Meta-Expose 라이브러리를 사용하는 서비스는 자신의 Enum 정의값을 자동으로 외부 API로 노출합니다.
    * 이 API는 서비스 코드에 추가 작업 없이 자동 구성\(auto config\)됩니다.

  * 중앙 Hub에서의 정합성 검증

    * `Meta-Expose-Hub`는 ServiceDiscovery를 통해 Enum API를 가진 서비스를 식별하고, 주기적으로 호출하여 Enum 정의값을 수집합니다.
    * 이를 기준 Enum과 비교해 정의의 일관성을 검증합니다.

  * 동적으로 서비스 식별

    * ServiceDiscovery는 Meta-Expose 의존성을 가진 서비스만을 식별해 관리합니다.
    * 신규 서비스도 자동으로 포함되어, 누락 없이 전체 시스템을 커버할 수 있습니다.

  * Grafana를 통한 모니터링

    * 검증 결과는 Prometheus에 지표\(metric\)로 수집되고, Grafana 대시보드를 통해 실시간으로 시각화됩니다.
    * 특정 Enum 정의가 불일치하거나 누락된 서비스가 있는 경우 대시보드에서 바로 확인할 수 있으며, 알림 연동도 가능합니다.
Grafana 대시보드에서 Enum 싱크가 맞는지 확인할 수 있습니다.

이 시스템을 통해 저희는 다음과 같은 효과를 얻을 수 있게 되었고, 마침내 Enum deserialize 에러에서 자유로워질 수 있었습니다.

  * Enum 변경 시, 모든 관련 서비스가 실제로 버전업 되었는지를 눈으로 확인 가능합니다.
  * 신규 Enum 추가 이후 배포 누락 서비스가 있다면 빠르게 감지하여 운영환경에서 발생할 수 있는 리스크를 사전에 제거할 수 있었습니다.
  * 신규 구성원이 Enum 정의 방식에 익숙하지 않더라도 자동 검증과 시각화 덕분에 실수를 방지할 수 있었습니다.

## 마치며

실수를 완전히 막을 순 없지만, 이를 문제로 확산되지 않도록 시스템 차원에서 방어하는 것은 개발자의 몫입니다. 그래서 저희는 예측 가능한 구조와 자동화된 감시 체계를 통해 오류를 사전에 차단하고자 했어요. 이러한 노력 덕분에, 수백 번의 배포와 확장되는 MSA 환경 속에서도 단 한 번의 Enum 이슈 없이 안정적인 서비스를 운영하는 성과를 얻을 수 있었습니다.

토스뱅크는 고객의 자산을 직접 다루는 은행 서비스 특성상, 1년에 한 번 발생할 수 있는 작은 버그라도 결코 가볍게 넘기지 않습니다. 성능만큼 안정성이 중요한 은행 도메인에서, 구조적으로 실수를 방지하고 예측 가능한 시스템을 함께 설계해 나가고 싶다면, 토스뱅크에 합류해 주세요.