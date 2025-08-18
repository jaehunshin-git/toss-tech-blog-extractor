# GitHub Actions로 개선하는 코드 리뷰 문화

**Date:** 2024년 2월 7일
**URL:** https://toss.tech/article/25431

---

토스페이먼츠는 결제의 다양한 맥락을 다루는 회사이기 때문에 코드 변경과 배포가 신중하게 이루어져야 하는데요. 이런 상황에서 코드 리뷰는 서비스의 안정성을 높일 수 있는 효과적인 방법 중 하나죠. 제가 속한 온보딩 플랫폼 팀에서도 코드 리뷰를 진행하고 있지만, 보다 면밀한 리뷰와 피드백 공유가 필요한 상황이었어요.

저는 코드 리뷰 문화의 가장 중요한 조건은 피드백의 속도와 PR 코멘트로 이루어지는 대화의 양, 두 가지라고 생각해요. 물론 리뷰의 질도 중요하지만, 리뷰 자체가 잘 이루어지려면 피드백 루프가 빠르게 돌아가는 것이 중요해요. 그래서 저는 피드백 루프가 시작되는 첫 단계인 ‘리뷰어 할당’부터 개선했어요. ‘리뷰어가 할당되면 피드백 루프가 빨라질 것이다’라는 가설을 세우고, 리뷰어를 자동으로 할당하는 자동화를 진행한 것이죠.

리뷰어 할당 자동화는 몇 가지 이유로 GitHub Actions로 개발했는데요. 먼저 GitHub Actions는 기능 구현과 유지보수가 간편하고 사용자가 많아서 접근성이 좋아요. 그리고 개발자들의 워크플로우가 GitHub Actions에서 제공하는 이벤트와 밀접하게 얽혀있어서 기능을 붙이기도 쉽고요.

물론 GitHub에서 [리뷰어 자동 할당 기능](https://docs.github.com/en/organizations/organizing-members-into-teams/managing-code-review-settings-for-your-team)을 기본으로 제공하고 있지만 커스터마이즈를 못한다는 단점이 있어요. 그래서 쉽게 커스터마이징할 수 있는 GitHub Actions로 자동화 기능을 직접 개발했어요.

#### [GitHub Actions](https://github.com/features/actions)는 GitHub에서 제공하는 자동화 툴인데요. 특정 [이벤트](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows)를 기반으로 [워크플로우](https://docs.github.com/en/actions/using-workflows/about-workflows)를 실행할 수 있게 해줘요. 많은 팀에서 GitHub Actions를 CI/CD에서만 사용하고 있지만, 사실 이벤트만 적절히 선택하면 그 이벤트 기반으로 많은 것을 자동화할 수 있어요.

## 1\. 리뷰어 지정하기

토스페이먼츠는 내부 워크플로우를 주로 타입스크립트로 개발하는데요. 유지보수의 편의성을 위해 이 워크플로우도 타입스크립트로 개발했어요. 워크플로우의 로직은 아주 간단해요. 정해진 리뷰어 목록에서 PR 생성자를 제외하고 랜덤으로 리뷰어를 선정해요. 그런 뒤, GitHub에서 제공하는 [toolkit](https://github.com/actions/toolkit)이라는 SDK를 통해 해당 리뷰어를 할당해요. 아주 간단한 로직이죠.
    
    
    async function main() {
      const selectedReviewer = selectRandomReviewer();
    
      await githubClient.rest.pulls.requestReviewers({
        owner: github.context.repo.owner,
        repo: github.context.repo.repo,
        pull_number: github.context.issue.number,
        reviewers: [selectedReviewer.githubName]
      });
    }
    
    function selectRandomReviewer() {
      const prCreator = github.context.payload.pull_request.user.login;
      const candidateReviewer = getCandidates().filter(
        (person) => person.githubName !== prCreator
      );
    
      return candidateReviewer[
        Math.floor(Math.random() * candidateReviewer.length)
      ];
    }

리뷰어가 될 수 있는 후보는 따로 정의한 yaml 파일에서 읽어오도록 설정했어요. yaml 파일은 리뷰어가 될 사용자들의 GitHub username과 Slack userId 쌍의 간단한 구조로 이루어져있어요. 새로운 리뷰어가 추가된다면, 코드 수정 없이 yaml 파일만 수정하면 돼요. 이 파일에 정의된 리뷰어 목록을 기반으로 PR이 생성될 때마다 워크플로우는 생성자 본인을 제외한 리뷰어 한 명을 지정해요. 
    
    
    reviewers:
      - githubName: 김토스
        slackUserId: toss-slack-user-id

이 워크플로우를 적용한 뒤 평균적으로 PR 리뷰가 되는 시간이 하루 내외로 짧아졌고, 코드 리뷰 자체에 더 익숙해지는 팀원도 늘어났어요. 실제로 워크플로우가 추가되기 전에 비해, 코드 리뷰의 코멘트 수도 평균적으로 2배 이상 많아졌어요.

또, 온보딩 플랫폼은 ‘계약’이라는 넓은 도메인을 다루고 있어서 개발팀 중에서도 특히나 많은 맥락을 가지고 있는데요. 이렇게 리뷰어를 무작위로 할당한 후에는 자신이 개발하지 않은 기능도 리뷰하게 되어서 팀 내에서 한두 명만이 알고 있었던 맥락을 점차 줄여나갈 수 있었어요. 이러한 것이 도움을 주어서인지, 온보딩 플랫폼의 운영 이슈 대응 시간은 작년에 비해 약 90% 정도 감소했어요. 회사 내에서 좋은 사례가 되어 다른 팀도 같은 워크플로우를 도입하기도 했고요.

## 2\. 리뷰어에게 알림 보내기

물론 개선이 필요한 부분도 있었어요. 처음에는 본인이 리뷰어로 지정된 걸 인지하기 어려웠어요. 리뷰어가 되면 GitHub이 메일로 알림을 보내는데요. 이메일을 자주 확인하지 않으면 본인이 리뷰어인 것을 알기 어려웠죠. 그래서 슬랙봇으로 리뷰어가 되었다는 메시지를 보내는 기능을 추가했어요.

앞서 살펴본 yaml 파일에 이미 리뷰어의 GitHub username과 Slack userId 정보가 있었기 때문에, slackClient를 호출하는 코드만 간단히 추가해서 문제를 해결했어요. 실제 코드는 아래와 같아요.
    
    
    async function main() {
      const selectedReviewer = selectRandomReviewer();
    
      await githubClient.rest.pulls.requestReviewers({
        owner: github.context.repo.owner,
        repo: github.context.repo.repo,
        pull_number: github.context.issue.number,
        reviewers: [selectedReviewer.githubName]
      });
    
      sendDirectMessage(selectReviewer);
    }
    
    async function sendDirectMessage(reviewer: IReviewer) {
      slackClient.chat.postMessage({
        text: createMessage(github.context),
        channel: reviewer.slackUserId
      });
    }

간단한 코드 작업으로 리뷰어 할당 알림을 훨씬 효과적으로 전달했어요. 실제로 팀원들이 리뷰를 시작하는 시점이 빨라진 것도 체감할 수 있었어요.

## 3\. 오늘 안에 리뷰할 수 있게 하기

리뷰 기간이 다소 지연되기도 했는데요. 여러 이유로 리뷰어가 리뷰 요청을 받은 당일에 확인하지 않으면, PR을 다시 안 보고 리뷰가 누락될 가능성이 높아졌어요. 그래서 구두로 다시 PR 리뷰를 요청하는 상황이 자주 발생하기도 했어요.

그래서 리뷰되지 않은 PR을 다시 알려주는 리마인드 워크플로우를 개발했어요. 이 워크플로우는 평일 오후 2시에 팀 채널로 전달돼요. 쉽게 인지할 수 있도록 점심시간이 끝나고 업무를 시작하는 타이밍에 알려주는 것이죠.

GitHub Actions는 PR에 대한 이벤트 외에도 다양한 이벤트 기능을 제공해요. 그 중 [cron 표현식](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/crontab.html#tag_20_25_07)을 이용해서 반복적으로 워크플로우를 [스케줄링](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)할 수 있는 이벤트가 있는데요. 아래와 같은 cron 표현식을 사용하면, 월요일부터 금요일까지 매주 오후 2시에 정의한 워크플로우가 동작해요.
    
    
    name: review-remind
    
    on:
      schedule:
        - cron: "0 5 * * 1-5" # GitHub Actions는 UTC 기준으로 스케쥴링 됨

이 스케줄 이벤트 덕분에 실제 코드 구현도 정말 간단해져요. 단순하게 특정 레포지토리에 Open 상태로 되어있는 PR이 리뷰가 되어있는지 체크하고, 리뷰가 되어있지 않은 PR 정보를 모아 팀 슬랙 채널로 전송하기만 하면 돼요.
    
    
    async function main() {
      const owner = process.env.GITHUB_REPOSITORY?.split("/")[0];
      const repo = process.env.GITHUB_REPOSITORY?.split("/")[1];
    
      const { data: pullRequests } = await githubClient.rest.pulls.list({
        owner,
        repo,
        state: "open",
        per_page: 100,
        sort: "updated",
        direction: "desc"
      });
    
      const messages = await collectMessages(pullRequests);
      sendMessage(messages);
    }
    
    async function collectMessages(pullRequests: IPullRequest[]): IMessage[] {
      return pullRequests
        .flatMap((pr) => {
          if (isDraft(pr) || isAlreadyReviewed(pr)) return [];
          else return [constructMessage(pr)];
        })
    }
    
    async function sendMessage(messages: IMessage[]) {
      if (messages.length === 0) return;
    
      const threadStartMessage = await slackClient.chat.postMessage({
        text: "리뷰해주세요!",
        channel: process.env.SLACK_CAHNNEL_ID
      });
    
      Promise.all(
        messages.map((message) => {
          slackClient.chat.postMessage({
            text: message.text,
            channel: process.env.SLACK_CAHNNEL_ID,
            thread_ts = threadStartMessage.ts
          });
        })
      );
    }

실제로 위 워크플로우가 동작하고 나면, 팀 슬랙 채널에는 오후 2시에 "리뷰해주세요\!" 스레드가 만들어지고 아래와 같이 리뷰가 필요한 PR의 목록들이 스레드의 댓글로 달리면서 리뷰어가 멘션 돼요. 이렇게 개선한 뒤, 팀원들이 밀린 코드 리뷰를 잊는 일이 점점 줄었어요.

## 번외: 공휴일에는 리뷰 건너뛰기

추석 전날 10분 만에 이루어진 개선을 하나 소개해 드릴게요. PR 리마인드 워크플로우가 cron 표현식 기반이라 주말에는 동작하지 않지만, 공휴일에는 동작하는 문제도 있었는데요. 이 문제도 아주 간단하게 해결했어요. 토스페이먼츠는 PG회사이기 때문에 매일 정산을 해요. 정산할 때 공휴일 정보는 매우 중요해서 오늘이 공휴일인지 확인할 수 있는 유틸리티가 내부에 이미 있었어요.

공휴일 유틸리티로 당일의 공휴일 여부를 확인하고, 공휴일이면 알림을 보내지 않도록 했어요. 코드는 아래와 같이 수정했어요.
    
    
    async function main() {
      if (isHoliday(new Date())) return;
    
      const owner = process.env.GITHUB_REPOSITORY?.split("/")[0];
      const repo = process.env.GITHUB_REPOSITORY?.split("/")[1];
    
      const { data: pullRequests } = await githubClient.rest.pulls.list({
        owner,
        repo,
        state: "open",
        per_page: 100,
        sort: "updated",
        direction: "desc",
        baseUrl: process.env.GITHUB_BASE_URI,
      });
    
      const messages = await collectMessages(pullRequests);
      sendMessage(messages);
    }
    
    function isHoliday(date: Date) {
      const formattedDate = formatDate(date);
      return utility.isHoliday(formattedDate);
    }

#### isHoliday\(\) 함수에서 date와 같은 값을 내부에서 초기화하는 방식으로도 사용할 수 있지만, 그렇게 되면 의존성에 의해 테스트하기 어려운 코드가 돼요. date와 같은 객체를 내부에서 생성하는 것이 아닌 외부 파라미터로 변경하게 되면 테스트하기 좋은 코드가 된답니다.

이렇게 간단한 개선을 통해, 공휴일에는 리뷰 리마인드를 건너뛰게 됐어요.

## 마치며

지금까지 자동화를 통해 코드 리뷰 문화를 개선하고 편의를 높였던 경험을 공유했어요. 이렇게 팀 내부의 업무 효율화를 위한 문제를 해결했을 때 받는 긍정적인 피드백은 큰 원동력이 되는 것 같아요. 팀원들의 시간을 줄여주고 효율화하는 작업에 의미를 느끼는 분이라면 한 번 도전해 보세요.

Write 김성일 Edit 한주연, 여인욱 Graphic 이나눔, 이은호