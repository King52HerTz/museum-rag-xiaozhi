package cn.xiangyu.museum

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import org.junit.Rule
import org.junit.Test

class MuseumNavigationTest {
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()

    @Test fun stickerNavigationSwitchesTabsAndRestoresSelection() {
        compose.onNodeWithText("儿童模式").performScrollTo().performClick()
        compose.onNode(hasText("探索") and hasClickAction()).assertIsSelected()
        compose.onNode(hasText("问阿帛") and hasClickAction()).performClick().assertIsSelected()
        compose.onNodeWithText("AI 服务将在 P2 接入。现在可以离线阅读首章，不会生成模拟回答。").assertExists()
        compose.onNode(hasText("我的手帐") and hasClickAction()).performClick()
        compose.activityRule.scenario.recreate()
        compose.onNode(hasText("我的手帐") and hasClickAction()).assertIsSelected()
        compose.onNodeWithText("我的旅行手帐").assertExists()
        compose.onNode(hasText("探索") and hasClickAction()).performClick().assertIsSelected()
        compose.onNodeWithText("今天，寄一封信给汉代").assertExists()
    }

    @Test fun childCanReadOfflineChapterAndSeeHonestAiState() {
        compose.onNodeWithText("儿童模式").performScrollTo().performClick()
        compose.activityRule.scenario.recreate()
        compose.onNodeWithText("今天，寄一封信给汉代").assertExists()
        compose.onNodeWithText("开始探索").performScrollTo().performClick()
        compose.onNodeWithText("直裾素纱单衣").assertExists()
        compose.onNodeWithText("问阿帛 · 尚未接入").performScrollTo().performClick()
        compose.onNodeWithText("AI 服务将在 P2 接入。现在可以离线阅读首章，不会生成模拟回答。").assertExists()
    }

    @Test fun adultModeUsesDifferentStoryAndCanSwitch() {
        compose.onNodeWithText("成人模式").performScrollTo().performClick()
        compose.onNodeWithText("从一件衣服，走进汉代生活").assertExists()
        compose.onNodeWithText("开始阅读").performScrollTo().performClick()
        compose.onNodeWithText("成人模式 · 切换模式").performScrollTo().performClick()
        compose.onNodeWithText("你想怎样开始这段旅行？").assertExists()
    }
}
