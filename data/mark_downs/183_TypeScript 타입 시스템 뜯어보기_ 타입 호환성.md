# TypeScript 타입 시스템 뜯어보기: 타입 호환성

**Date:** 2022년 10월 26일
**URL:** https://toss.tech/article/typescript-type-compatibility

---

토스 Node.js 챕터에서는 높은 코드 가독성과 품질을 위해 TypeScript의 타입 시스템을 적극적으로 활용하고 있고 이에 대한 이해도를 높이기 위해 스터디를 꾸준히 진행하고 있습니다. TypeScript의 타입 시스템에 대해 공부해보던 중 알게된 흥미로운 몇가지 토픽들을 소개하려 합니다. 그 중 한가지로 이번글에서는 “타입 호환성 \(type compatibility\)”에 대해 알아보고자 합니다.

TypeScript 공식문서 [타입 호환성에 관한 글](https://www.typescriptlang.org/ko/docs/handbook/type-compatibility.html)을 보면 아래와 같이 소개하고 있습니다.

> TypeScript의 타입 호환성은 구조적 서브타이핑\(structural subtyping\)을 기반으로 합니다. 구조적 타이핑이란 오직 멤버만으로 타입을 관계시키는 방식입니다. 명목적 타이핑\(nominal typing\)과는 대조적입니다. TypeScript의 구조적 타입 시스템의 기본 규칙은 y가 최소한 x와 동일한 멤버를 가지고 있다면 x와 y는 호환된다는 것입니다.

위 내용에 대해 하나씩 이해해봅시다. 우선 강한 타입 시스템을 통해 높은 가독성과 코드 품질을 지향하는 TypeScript가 왜 타입 호환성을 지원하는 것일까요? 이 경우 타입 안정성에 문제가 생기게 되는 것은 아닐까요? 아래 예시를 통해 타입 호환성이 왜 필요한지 살펴보겠습니다.

위와 같이 음식 `Food` 타입의 객체를 인자로 받아 간단한 칼로리 계산 공식으로 주어진 음식의 칼로리를 구하는 `calculateCalorie` 함수가 있습니다. 타입과 함수는 아래와 같이 구현되어 있습니다.
    
    
    type Food = {
      /** 각 영양소에 대한 gram 중량값 */
      protein: number;
      carbohydrates: number;
      fat: number;
    }
    
    function calculateCalorie(food: Food){
      return food.protein * 4
        + food.carbohydrates * 4
        + food.fat * 9
    }

한편, 개발자가 코드를 작성하는 과정에서 \(의도했거나 혹은 실수로\) `calculateCalorie` 함수 인자에 여러가지 타입의 객체를 전달해본다고 가정해봅시다. 이 경우 TypeScript 타입 시스템은 프로그램이 타입 오류를 일으킬 가능성을 검사하게 됩니다.

위 3가지 케이스에 대해 Type Checker가 어떻게 판단하는 것이 좋을까요?

개발자가 정의한 `Food` 타입과 동일한 타입인 경우 \(1번\) 오류 없음이 명확하며, `Computer` 타입과 같이 다른 타입이며 칼로리 계산이 불가능한 경우 \(2번\) 오류로 판단하는 것이 명확합니다. 하지만, 햄버거를 의미하며 음식의 한 종류인 `Burger` 타입이 전달되는 경우 \(3번\) 어떻게 판단하는 것이 맞을까요?
    
    
    type Burger = Food & {
      /** 햄버거 브랜드 이름 */
      burgerBrand: string;
    }

심지어 `Burger` 타입이 위와 같이 `Food` 타입을 상속하며 칼로리 계산에 필요한 모든 프로퍼티를 포함하고 있어 런타임 상에서 정상적으로 동작한다면 이를 타입 오류라고 판단하는게 올바른 걸까요?

이처럼 실제로 정상적으로 동작할 수 있는 올바른 코드라면 타입 시스템은 개발자의 의도에 맞게 유연하게 대응하여 타입 호환성을 지원하는 것이 더 좋을 수 있습니다. 이러한 유연성을 위해 TypeScript 타입 시스템은 부분적으로 타입 호환을 지원하고 있습니다.

한편 위에 예시에서 `Computer` 타입 사례처럼 타입오류로 판단하는 것이 명확한 경우가 있으며, 타입 안정성을 해치면서까지 유연함을 제공하는 것은 바람직하지 못합니다. 이를 위해서는 어떠한 경우에 호환을 허용할 것인지에 대한 명확한 규칙이 필요합니다. 이러한 규칙 중 프로그래밍 언어들에서 널리 활용되는 방식으로 명목적 서브타이핑\(nominal subtyping\)과 구조적 서브타이핑\(structural subtpying\)이 있습니다.

명목적 서브타이핑은 아래와 같이 타입 정의 시에 상속 관계임을 명확히 명시한 경우에만 타입 호환을 허용하는 것입니다. 이 방법을 통해 타입 오류가 발생할 가능성을 배제하고, 개발자의 명확한 의도를 반영할 수 있습니다.
    
    
    /** 상속 관계 명시 */
    type Burger = Food & {
      burgerBrand: string;
    }
    
    const burger: Burger = {
      protein: 29,
      carbohydrates: 48,
      fat: 13,
      burgerBrand: '버거킹'
    }
    
    const calorie = calculateCalorie(burger)
    /** 타입검사결과 : 오류없음 (OK) */
    
    

한편, 구조적 서브타이핑은 아래와 같이 상속 관계가 명시되어 있지 않더라도 객체의 프로퍼티를 기반으로 사용처에서 사용함에 문제가 없다면 타입 호환을 허용하는 방식입니다. 아래 예시를 보면 비록 상속 관계임을 명시하지는 않았지만 `burger` 변수는 `Food` 타입의 프로퍼티를 모두 포함하고 있고 따라서`calculateCalorie` 함수 실행과정에서 오류가 발생하지 않습니다.
    
    
    const burger = {
      protein: 29,
      carbohydrates: 48,
      fat: 13,
      burgerBrand: '버거킹'
    }
    
    const calorie = calculateCalorie(burger)
    /** 타입검사결과 : 오류없음 (OK) */

구조적 서브타이핑 방식은 타입 시스템이 객체의 프로퍼티를 체크하는 과정을 수행해주므로써, 명목적 서브타이핑과 동일한 효과를 내면서도 개발자가 상속 관계를 명시해주어야 하는 수고를 덜어주게 됩니다. 참고로, 구조적 서브타이핑은 “만약 어떤 새가 오리처럼 걷고, 헤엄치고, 꽥꽥거리는 소리를 낸다면 나는 그 새를 오리라고 부를 것이다.” 라는 의미에서 덕 타이핑 \(duck typing\) 이라고도 합니다.

TypeScript Type Checker는 구조적 서브타이핑을 기반으로 타입 호환을 판단합니다.

TypeScript는 구조적 서브타이핑을 지원하며, 명목적 서브타이핑만 지원하는 C\#, Java 등의 언어는 명시적으로 상속 관계를 명시해주어야 타입 호환이 가능합니다.

> 💡 한편, 여기서부터 좀 더 본격적인 이야기를 다루어 보겠습니다.

위 구조적 서브타이핑 예시의 코드는 타입 호환성에 따라 타입 오류가 발생하지 않지만, 아래 코드의 경우 컴파일 과정에서 `Argument is not assignable to parameter of type 'Food'` 라는 타입 오류가 발생하게 됩니다. 글을 더 읽으시기에 앞서 실제로 [TS Playground](https://www.typescriptlang.org/play#code/C4TwDgpgBAYg9nAJlAvFA3lAUASAPQBUBUggDVSCAY4ImjgMYOALo1IADNgOqtQDmATgIYC2UgiJOBJ9sBINVAJ4sUKGHZxgEAJYA7AFxRFAV24AjCOwDcEqAGNO7LXAAWIRFzkBnVRu26DkgGadgjzTv1YAvlhYbuqKRsDycIrGnAA2RgDCcXDsIAAUbgiIqvBIAJTohuwQwOrs0ZlIAHTSsgrRxAAsUADUUJWIVSZmlta2EHaiUM1tHVUewEMAnAFBoJBQAEJlrLqosFlQAGQYhloruotcitlQdsDsSqwGgVhGUedQ++yr7ACMqssva2iFOLVyJSqABMUwANIZuuYrDZPANVI0ABwQ9yeVRvADMKKeB3YR04J1UAHJACE9gAcawCdC0TZncHpMTLEUiA3usGYlkqk0s9Xm88pJCMRAAMLgFDxwABNYAagaggAaawA-NVBVIASMcAGp1QQBjo4AZcdE4lpike3N0wPWfwB9RB4MhpmhfThDmGyMME3RWL2uPxhKgpMp1Nu9119I5IFZcXZjM5+vYwL5UAFUBFEulcsVKo1WqCvseDKZGKD8SSofSxpkgJUUFB2KhvVh9gR9tRXigmOx4bdp09VICUckXe7Pd7fZ7McFgBDx+Oy+VQZVQQAR45qxEA)를 통해 오류를 확인해보시고 다양하게 테스트해보시는 것도 추천합니다.
    
    
    const calorie = calculateCalorie({
      protein: 29,
      carbohydrates: 48,
      fat: 13,
      burgerBrand: '버거킹'
    })
    /** 타임검사결과 : 오류 (NOT OK)*/

왜 위 코드는 타입 호환이 지원되지 않는 것일까요? 처음에 이 오류를 마주쳤을 때 이런저런 테스트를 해보며 함수에 값을 바로 인자로 전달하는 경우만 타입 호환이 지원되지 않는 것 같다고 유추하기는 했으나 조금 더 구체적인 규칙과 이렇게 예외가 발생하는 이유에 대해 이해해보고자 했습니다.

결과적으로 TypeScript 컴파일러 코드 상의 구현로직과 위 이슈와 연관된 [TypeScript Github PR](https://github.com/Microsoft/TypeScript/pull/3823)을 통해 이해할 수 있었습니다. 이에 대해 알아보기 위해 우선 TypeScript 컴파일러가 동작하는 방식에 대해 간략히 살펴보겠습니다.

TypeScript 컴파일러가 동작하는 방식에 관해 아래 영상에 자세히 소개되어 있으며, 이 중 몇가지 내용만 요약하여 살펴보겠습니다.

<https://www.youtube.com/watch?v=X8k_4tZ16qU>

TypeScript 컴파일러의 역할은 TypeScript 소스코드를 AST \(Abstract Syntax Tree\)로 변환한 뒤, 타입 검사를 수행하고, 그 후 JavaScript 소스코드로 변환하는 과정을 담당합니다.

TypeScript 소스코드를 AST로 변환하는 과정은 `parser.ts, scanner.ts` , 타입 검사를 수행하는 과정은 `binder.ts, checker.ts`, AST를 JavaScript 소스코드로 변환하는 과정은 `emitter.ts, transformer.ts` 등의 파일이 담당하고 있습니다.

실제로 [TypeScript Github의 compiler 디렉토리](https://github.com/microsoft/TypeScript/tree/main/src/compiler)에 가면 위 코드 파일이 어떤식으로 구현되어 있는지 확인해볼 수 있으며, 이번 글에서 다루고 있는 주제인 구조적 서브타이핑과 타입 호환에 관한 부분은 타입 검사와 가장 연관이 높은 `checker.ts` 파일의 `hasExcessProperties()` 함수에서 처리하고 있었습니다.

아래는 `checker.ts`[코드](https://raw.githubusercontent.com/microsoft/TypeScript/main/src/compiler/checker.ts) 중 타입 호환의 예외가 발생하는 지점의 코드를 주요한 부분만 남기고 간소화한 것입니다. 주석과 함께 봐주시면 좋을 것 같습니다.
    
    
    /** 함수 매개변수에 전달된 값이 FreshLiteral인 경우 true가 됩니다. */
    const isPerformingExcessPropertyChecks =
        getObjectFlags(source) & ObjectFlags.FreshLiteral;
    
    if (isPerformingExcessPropertyChecks) {
        /** 이 경우 아래 로직이 실행되는데,
         * hasExcessProperties() 함수는
         * excess property가 있는 경우 에러를 반환하게 됩니다.
         * 즉, property가 정확히 일치하는 경우만 허용하는 것으로
         * 타입 호환을 허용하지 않는 것과 같은 의미입니다. */
        if (hasExcessProperties(source as FreshObjectLiteralType)) {
            reportError();
        }
    }
    /**
     * FreshLiteral이 아닌 경우 위 분기를 skip하게 되며,
     * 타입 호환을 허용하게 됩니다. */

지면상 다소 간소화한 코드만 남겨두었지만, 함수에 인자로 들어온 값이 `FreshLiteral` 인지 아닌지 여부에 따라 조건분기가 발생하여 타입 호환 허용 여부가 결정된다는 것을 확인할 수 있었습니다.

그렇다면 `Fresh Literal` 이란 무엇이며, 왜 이 경우에는 타입 호환의 예외가 발생하도록 되어 있는 것일까요?

TypeScript는 구조적 서브타이핑에 기반한 타입 호환의 예외 조건과 관련하여 [신선도 \(Freshness\)](https://radlohead.gitbook.io/typescript-deep-dive/type-system/freshness) 라는 개념을 제공합니다. 모든 object literal은 초기에 “fresh” 하다고 간주되며, 타입 단언 \(type assertion\) 을 하거나, 타입 추론에 의해 object literal의 타입이 확장되면 “freshness”가 사라지게 됩니다. 특정한 변수에 object literal을 할당하는 경우 이 2가지 중 한가지가 발생하게 되므로 “freshness”가 사라지게 되며, 함수에 인자로 object literal을 바로 전달하는 경우에는 “fresh”한 상태로 전달됩니다.

한편, [TypeScript Github PR \(2015년 7월\) 의 논의](https://github.com/Microsoft/TypeScript/pull/3823)에 따르면, fresh object인 경우에는 예외적으로 타입 호환을 허용하지 않기로 했음을 확인할 수 있습니다. 그러한 이유에 대해 살펴보겠습니다.
    
    
    /** 부작용 1
     * 코드를 읽는 다른 개발자가 calculateCalorie 함수가
     * burgerBrand를 사용한다고 오해할 수 있음 */
    const calorie1 = calculateCalorie({
      protein: 29,
      carbohydrates: 48,
      fat: 13,
      burgerBrand: '버거킹'
    })
    
    /** 부작용 2
     * birgerBrand 라는 오타가 발생하더라도
     * excess property이기 때문에 호환에 의해 오류가
     * 발견되지 않음 */
    const calorie2 = calculateCalorie({
      protein: 29,
      carbohydrates: 48,
      fat: 13,
      birgerBrand: '버거킹'
    })

구조적 서브타이핑에 기반한 타입 호환은 유연함을 제공한다는 이점이 있지만, 위 코드 사례와 같이 코드를 읽는 다른 개발자의 입장에서 함수가 실제 다루는 것보다 더 많은 데이터를 받아들인다는 오해를 불러일으킬 수 있고, 프로퍼티 키에 대한 오타가 발생하더라도 오류가 확인되지 않는 부작용이 있습니다.

한편, fresh object를 함수에 인자로 전달한 경우, 이는 특정한 변수에 할당되지 않았으므로 어차피 해당 함수에서만 사용되고 다른 곳에서 사용되지 않습니다. 이 경우 유연함에 대한 이점보다는 부작용을 발생시킬 가능성이 높으므로 굳이 구조적 서브타이핑을 지원해야할 이유가 없습니다.

TypeScript Type Checker는 구조적 서브타이핑을 기반으로 타입 호환을 판단하되,Freshness에 따라 예외를 둡니다.

이처럼 타입 호환성은 유연함이라는 이점을 제공하지만 그로 인해 부작용이 발생할 수 있으므로, 이에 대한 절충안으로 타입 호환을 제공해서 얻는 이점이 거의 없는 fresh object에 대해서는 호환성을 지원하지 않기로 논의되어 TypeScript 컴파일러 코드에 반영된 것을 확인해볼 수 있었습니다.

한편, 그럼에도 개발자가 fresh object에 대해서 타입 호환을 허용하고자 한다면 아래와 같이 함수 매개변수 타입에 index signature를 포함시켜두어 명시적으로 타입 호환을 허용시키는 것이 가능합니다. 또는 tsconfig 상에 `suppressExcessPropertyErrors` 를 true로 설정하는 방식도 가능합니다. \(이 또한 [동일한 PR 논의](https://github.com/Microsoft/TypeScript/pull/3823)에 정의되어 있습니다.\)
    
    
    type Food = {
      protein: number;
      carbohydrates: number;
      fat: number;
      [x:string]: any                  /** index signature */
    }
    
    const calorie = calculateCalorie({
      protein: 29,
      carbohydrates: 48,
      fat: 13,
      burgerBrand: '버거킹'
    })
    /** 타임검사결과 : 오류없음 (OK) */
    
    

또한 반대로 모든 경우에 대해 타입 호환을 허용하지 않도록 강제하는 것도 가능한데 이를 위해 사용할 수 있는 기법이 Branded type \(또는 Branding type\) 입니다. 아래와 같이 의도적으로 `__brand` 와 같은 프로퍼티를 추가시켜, 개발자가 함수의 매개변수로 정의한 타입 외에는 호환이 될 수 없도록 강제하는 기법입니다. 온도\(섭씨, 화씨\)나 화폐단위\(원, 달러, 유로\)와 같이 같이 `number` 타입이지만 서로 다를 의미를 가질 수 있어 명시적인 구분이 필요할 때 사용해볼 수 있습니다.
    
    
    type Brand<K, T> = K & { __brand: T};
    type Food = Brand<{
      protein: number;
      carbohydrates: number;
      fat: number;
    }, 'Food'>
    
    const burger = {
      protein: 100,
      carbohydrates: 100,
      fat: 100,
      burgerBrand: '버거킹'
    }
    
    calculateCalorie(burger)
    /** 타임검사결과 : 오류 (NOT OK) */
    
    

앞선 글을 통해 이해한 타입 호환의 이점과 부작용에 대한 이해를 바탕으로 개발자는 자신의 프로젝트를 진행하는 과정에서 필요에 맞게 `index signature`, `tsconfig > suppressExcessPropertyErrors`, `branded type` 등을 통해 타입 호환성의 범위를 선택하여 개발하는 것이 가능할 것입니다.

TypeScript Type Checker는 내부적인 규칙에 따라 타입 호환을 판단하지만,개발자가 필요에 따라 선택하는 것이 가능합니다.

이번글의 내용을 모두 요약하면 아래와 같습니다.

  * 타입 검사의 안정성과 유연함 사이에서 절충안으로 도입된 개념이 타입 호환성입니다. 그리고 타입 호환성을 지원하는 방법과 관련하여 개발자에게 명시적 선언을 어디까지 요구할 것인지에 대한 선택지가 존재합니다.
  * TypeScript는 구조적 서브타이핑에 기반한 타입 호환을 통해 개발자의 명시적 선언을 줄여주는 한편 이로 인한 부작용을 개선하고자 freshness에 기반한 예외조건을 두었고, Index Signature와 Branded type 등의 방식을 통해 개발자가 명시적으로 선택할 수 있는 선택지를 만들어두었습니다.
  * 프로그래밍 언어마다 타입 검사가 동작하는 방식이 다르며 이는 해당 언어를 개발한 커뮤니티의 논의와 의사결정에 따라 선택된 결과라고 볼 수 있습니다. 본 주제 외에도 TypeScript 컴파일러 코드와 Github PR을 살펴보면 흥미로운 논의와 토픽들을 확인해볼 수 있습니다.

토스 Node.js 챕터는 토스의 다양한 제품과 라이브러리 개발을 위해 팀원들의 지속적인 성장이 중요하다고 믿으며, 이를 위해 꾸준히 공부하고 공유하는 자리를 가지고 있으니 많은 관심 부탁드립니다.

토스 Node.js Chapter 채용 공고 👉 [바로가기](https://toss.im/career/jobs?search=node.js)

감사합니다.