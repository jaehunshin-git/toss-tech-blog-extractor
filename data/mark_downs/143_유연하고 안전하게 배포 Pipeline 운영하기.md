# 유연하고 안전하게 배포 Pipeline 운영하기

**Date:** 2023년 10월 12일
**URL:** https://toss.tech/article/slash23-devops

---

토스뱅크에는 400개가 넘는 배포 Pipeline 이 있습니다. Pipeline의 개수가 많아지고, 종류가 다양해지고, 동작이 복잡해지며 여러 어려움이 생기는데요. 토스뱅크에서 Pipeline을 유연하고 안전하게 운영하기 위해 노력한 이야기를 소개해 보려 합니다.

## Pipeline이란?

반복하는 일을 자동화하는 시스템을 말합니다. 서버 프로그램을 빌드하고 배포하는 Pipeline 이 가장 대표적인데요. 라이브러리를 업로드하거나 운영 작업을 자동화하는 데에도 많이 활용합니다. Micro Service Architecture를 적극적으로 활용하는 토스뱅크에서는 하루에도 수십~수백 번 서버를 배포하기 때문에, Pipeline 은 동료 개발자분들이 일상적으로 가장 많이 사용하는 시스템 중 하나입니다.

## Pipeline에 필요한 것

토스뱅크에서는 새로운 서비스가 자주 생기고 서비스의 동작이 자주 변하기 때문에 Pipeline을 빠르게 만들고 수정할 수 있어야 합니다. 서비스를 안정적으로 운영하려면 Pipeline들이 일관성 있게 동작해야 하고요. 그리고 모든 Pipeline에서 반드시 지켜야 하는 Compliance 요건이 있습니다. 토스뱅크와 같은 금융권 회사들을 전자금융감독규정이 적용됩니다. 서버를 배포할 때 동료끼리 검증을 하는 등의 절차를 Pipeline에서 준수해야 합니다. 저희는 이런 요건들을 잘 충족하기 위해서는 Pipeline 설정을 중앙화하는 것이 효율적이라고 판단하였고, 여러 스쿼드가 사용하는 Pipeline 설정을 한 곳에 모아두고 DevOps Engineer가 주도적으로 운영하고 있습니다.

## GoCD

Pipeline 도구로는 Jenkins, GitHub Actions 등 여러 가지가 있는데요. 토스뱅크에서는 GoCD를 주로 사용합니다. GoCD는 Pipeline을 정의에 따라 Server가 작업을 할당하고 Agent가 실행하는 구조입니다. 널리 사용되는 Jenkins 와 비슷합니다.

## 첫 번째 어려움: 가시성

GoCD에서 새로운 Pipeline을 만들 때에는 웹 UI에서 Pipeline Wizard를 사용합니다. Pipeline 개수가 많지 않을 때에는 이렇게 Pipeline 을 만들고 수정해도 큰 어려움이 없었지만, Pipeline 개수가 많아지면서 어려움을 겪었습니다.

토스뱅크에는 서비스 빌드/배포 Pipeline이 281개, 작업 자동화 Pipeline이 76개, 이외 Pipeline이 47개, 도합 400개가 넘는 Pipeline이 있습니다. Pipeline이 많으면 웹 UI에서는 어떤 Pipeline이 있는지 확인하는 것부터 쉽지 않습니다. 한 화면에서 보이는 Pipeline 개수가 많지 않기 때문인데요. 자신이 찾는 Pipeline의 이름을 알고 있다면 검색해서 찾을 수 있지만, 그렇지 않다면 모든 Pipeline을 훑어봐야 합니다.

그리고 Pipeline 하나의 설정을 보는 것도 어렵습니다. 일반적으로 Pipeline은 여러 단계를 갖는데요. 웹 UI에서는 한 단계씩 볼 수 있기 때문에 각 단계의 순서와 동작을 확인하려면 여러 페이지를 왔다 갔다 해야 합니다. 마찬가지로 서로 다른 Pipeline의 설정을 비교하기도 어렵고요.

가장 큰 문제는 Pipeline 설정이 어떻게 변했는지 알기 어렵다는 것입니다. Pipeline의 동작은 계속 변합니다. 배포 방식이 달라지기도 하고 Compliance 요건이 변하기도 하지요. 하지만 웹 UI에서는 지금의 설정만 볼 수 있기 때문에, Pipeline 동작이 무언가 이상해서 확인해 볼 때에 언제 어떻게 설정이 변했는지 알기 어렵습니다.

## Pipeline as Code

이때에는 Pipeline as Code 가 도움이 되었습니다. Pipeline 을 웹 UI에서 정의하지 않고 코드로 표현하여 Git에 저장하는 것을 말하는데요. 저희는 Pipeline 설정을 YAML 파일로 작성하여 Git에 저장하고, GoCD 서버와 연동하는 gocd-yaml-config-plugin을 활용했습니다.

모든 Pipeline 설정이 파일로 저장되어 있으니 어떤 Pipeline 이 있는지 Git 저장소에서 한 번에 볼 수 있습니다. 수백 개의 Pipeline 이 있더라도 한 폴더에서 모두 확인할 수 있지요.

여러 단계로 이루어진 Pipeline 설정도 한 파일에서 모든 설정과 단계를 볼 수 있습니다.

그리고 Pipeline 설정 파일이 Git 저장소에서 Version Control 되기 때문에 언제 어떻게 변경되었는지 확인할 수 있습니다.

## 두 번째 어려움: 생산성

토스뱅크의 Pipeline 개수를 약 6개월 간격으로 집계해 보면 1년에 2배 이상으로 많아지는 것을 볼 수 있습니다. 토스뱅크는 Micro Service Architecture를 적극적으로 활용하고 있어 새로운 서비스를 자주 만들기 때문에 Pipeline 을 빠르고 정확하게 만들 수 있어야 합니다. 한편, 새로운 서비스는 기존 서비스와 기술 스택과 구조가 비슷한 경우가 많기 때문에, 이미 있는 Pipeline 설정을 복사 붙여넣기해서 새로운 Pipeline을 만들 때가 많습니다. 이때 설정을 잘못 붙여넣기도 하고, 바꾸어야 할 부분을 빼먹는 등 실수를 하기 쉽습니다. 그리고 모든 Pipeline에 공통된 변경 사항이 있을 때에는 모든 파일을 수정해야 하는데, 이때에도 실수를 하기 쉽습니다. 잘못된 설정을 찾아내고 바로잡는 것은 Pipeline을 빠르게 만들고 수정하는 일에 걸림돌이 되었지요.

## GoCD Template

이 문제에는 GoCD Template이 도움 되었습니다. Pipeline 동작을 추상화해서 Template으로 만들고 여러 Pipeline에서 공유하는 기능인데요. 앞서 살펴 본 gocd-yaml-config-plugin과도 함께 사용할 수 있습니다.

공통 설정은 Template을 지정하는 한 줄로 대체되어 훨씬 간결해지고, 서로 달라야 하는 설정은 변수로 주입할 수 있습니다. 공통 변경 사항이 있을 때에는 Template에서 변경하면 모두에게 적용되고요. Pipeline을 만들고 수정할 때 실수를 할 여지가 상당히 줄어듭니다.

## 세 번째 어려움: 확장성

프로그래밍에서 변경에 유연하게 대처할 수 있는 코드를 확장성이 높다고 이야기하는데요. Pipeline 역시 설정을 변경할 때 유연하게 대처할 수 있어야 합니다. 하지만 지금까지 살펴 본 방식으로는 Pipeline 설정은 Git에서, Template 설정은 웹 UI 에서 봐야 하기 때문에 둘을 비교하면서 Template을 수정하는 것이 꽤나 불편했습니다. 그리고 Template을 수정하면 많은 Pipeline에 한 번에 적용되기 때문에 실수를 했을 때 영향이 굉장히 큽니다. 결과적으로 Pipeline 설정을 유연하게 변경하기 어려웠는데요.

## Helm Template

저희는 Template Rendering 도구인 Helm Template으로 이 문제를 해결해 보기로 했습니다. Helm Template은 공통 부분을 Template으로 만들고 고유한 부분을 Values로 주입하여 Rendering 할 수 있으며, 조건문과 반복문, 변수를 활용하여 꽤나 복잡한 내용도 표현할 수 있습니다.

Helm Template은 YAML 파일을 잘 지원하기 때문에 앞서 보았던 gocd-yaml-config-plugin과도 잘 어울립니다. YAML로 된 Pipeline 설정을 추상화하여 Helm Template으로 만들면 GoCD Template을 대체할 수 있을 뿐만 아니라, GoCD Template에서 지원되지 않는 부분도 Template으로 사용할 수 있습니다. 이렇게 만든 Helm Template은 파일로 저장되기 때문에, Pipeline 설정 파일과 동일한 Git 저장소에 두면 Pipeline 설정과 Template 설정을 한 곳에서 확인할 수 있습니다.

그리고 Helm Template의 조건문을 활용하면 Template 변경을 일부 Pipeline에서만 테스트해 볼 수도 있습니다. 전체 Pipeline에 적용하기 전에 테스트용 Pipeline에서 충분히 동작을 검증할 수 있게 되었고, Template 변경 실수가 모든 Pipeline에 영향을 주는 일이 줄어들었습니다.

한편, Helm Template을 활용하면 호환성에서도 이점이 있습니다. GoCD Template 등 Pipeline 도구 고유의 기능은 그 도구에서만 사용할 수 있지만, Helm Template의 Values 파일은 Pipeline 도구와 무관한 추상적인 설정을 담고 있습니다. GitHub Actions 등 다른 Pipeline 도구를 사용할 때에는 그에 맞도록 Template 파일만 새로 작성하면 Values 파일을 재사용할 수 있습니다.

## 네 번째 어려움: 복잡성

Pipeline Template은 시간이 지나며 점점 복잡해집니다. 2023년 1월 기준으로 토스뱅크의 Pipeline은 5가지 Type과 72개의 설정값이 있고, Template 파일 길이를 모두 더하면 1,182 줄이 됩니다. Template이 복잡할수록 실수로 오타를 내거나 의도하지 않은 변경을 만들기 쉽습니다. Helm Template 문법은 일반 프로그래밍 언어만큼 직관적이지는 않기 때문에 더욱 그렇습니다. Pipeline Template을 잘못 수정해서 배포가 안되거나 잘못된 배포가 되는 일이 종종 있었는데요.

## CI

저희는 CI를 도입해 보기로 했습니다. CI는 Continuous Integration의 약자로, 변경 사항에 대하여 자동으로 검증을 진행하고 성공했을 때에만 반영하는 것을 말합니다. Template 파일은 develop 브랜치에서만 수정하고, 검증을 통과했을 때에만 master 브랜치에 반영되도록 GitHub Actions로 CI를 구성했습니다.

검증은 develop 브랜치에 변경 사항이 생기면 모든 Pipeline 설정 파일을 다시 Rendering 하는 것입니다. 의도한 변경은 이미 반영되어 있을 것입니다. 반면 다시 Rendering 할 때 바뀌는 파일 내용은 의도하지 않은 변경일 확률이 높습니다. CI를 수행하는 동안 Pipeline 설정 파일 내용이 바뀌었다면 한 번 확인해 봐야 합니다. 이때에는 검증이 실패하고, 사내 메신저로 알람을 보내 작업자가 다시 확인하도록 합니다.

## Kubernetes Object CI

한편, 토스뱅크의 채널계 서비스는 Kubernetes에서 운영하고 있으며, 서비스를 배포할 때에는 Helm Template을 사용해 Kubernetes Object를 배포합니다. 2023년 1월 기준으로 토스뱅크의 Kubernetes Object Template은 7가지 Object와 110개의 설정 값이 있고, Template 파일 길이를 모두 더하면 762줄이 됩니다. 앞서 살펴 본 Pipeline Template처럼 복잡한 Template을 사용하기 때문에, 마찬가지로 Template을 수정할 때 실수를 하기 쉬웠습니다.

한편, Kubernetes Object는 Pipeline 설정과 다른 점이 있었는데요. Helm Template으로 Rendering 한 결과를 Kubernetes에 배포할 뿐, Git에 파일로 저장하지 않는다는 것입니다. CI로 검증을 수행할 때에 비교할 파일이 없는 것인데요. 그래서 검증용 Kubernetes Object 파일을 Git에 저장하기로 했습니다.

CI를 수행할 때에는 모든 검증용 Kubernetes Object 파일을 다시 Rendering 합니다. 의도한 변경은 이미 검증용 Kubernetes Object 파일에 반영되어 있을 것이고, 다시 Rendering 할 때 바뀌는 파일 내용은 의도하지 않았을 확률이 높습니다. 이때에는 Pipeline CI와 마찬가지로 사내 메신저 알람을 보냅니다.

CI를 수행하는 동안 Pipeline 설정 파일과 검증용 Kubernetes Object 파일 모두 내용이 바뀌지 않는다면, 의도하지 않은 변경 사항이 없는 것으로 간주하고 master 브랜치에 자동으로 반영합니다. 이후에 실행하는 Pipeline 과 이후에 배포되는 Kubernetes Object는 변경 사항이 반영된 Template을 사용합니다.

## 마치며

마무리하며 글의 내용을 요약해 보면 아래와 같습니다.

  * Pipeline이 너무 많아서 어떤 것들이 있고 어떻게 설정되어 있는지 확인하기 어렵다면 Pipeline as Code가 도움이 됩니다.
  * Pipeline을 빠르고 정확하게 만들기 위해서는 Template 기능이 도움이 됩니다.
  * Pipeline Template을 수정하기 어렵다면 Helm Template이 도움이 됩니다.
  * Pipeline 이 너무 복잡해서 수정할 때 실수가 많다면 CI를 도입하는 것이 도움이 됩니다.

Pipeline as Code는 일반적으로 Version-control이 되는 Pipeline을 뜻하는 경우가 많습니다. Pipeline 설정을 파일 형태로 저장하고 Git에서 확인하는 것까지를 말하지요. 여기에 Helm Template으로 Programmable 한 특성을, CI로 Testable 한 특성을 더하면 정말 Code처럼 유연하고 안전하게 Pipeline을 운영할 수 있다고 생각합니다. 비슷한 고민을 하셨던 분이 계시다면 조금이나마 도움이 되었으면 좋겠습니다.