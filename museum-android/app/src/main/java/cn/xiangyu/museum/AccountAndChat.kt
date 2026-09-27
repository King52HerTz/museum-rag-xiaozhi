package cn.xiangyu.museum

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview

@Composable
fun AccountContent(state: MuseumState, onSubmit: (String, String, String, Boolean) -> Unit,
                   modifier: Modifier = Modifier) {
    var register by remember { mutableStateOf(false) }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var endpoint by remember(state.endpoint) { mutableStateOf(state.endpoint) }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(Space.medium)) {
        Text("把你的文物旅行记，留在自己的手帐里", style = MaterialTheme.typography.headlineLarge)
        Text("请由成人协助注册，不需要填写姓名、年龄或学校。", style = MaterialTheme.typography.bodyMedium)
        if (state.restoring) {
            CircularProgressIndicator()
            Text("正在恢复登录")
        } else {
            MuseumField(username, { username = it }, "账号", enabled = !state.authBusy)
            MuseumField(password, { password = it }, "密码", password = true, enabled = !state.authBusy)
            MuseumField(endpoint, { endpoint = it }, "服务地址", enabled = !state.authBusy)
            Text(if (BuildConfig.DEBUG) "调试版：模拟器使用 10.0.2.2 访问电脑；真机填写可达的服务地址。HTTP 仅用于可信开发网络。"
                else "请使用 HTTPS 服务地址。", style = MaterialTheme.typography.bodySmall)
            state.error?.let { MuseumNotice(it, error = true) }
            MuseumButton(onClick = { onSubmit(endpoint, username, password, register); password = "" },
                enabled = !state.authBusy && username.isNotBlank() && password.isNotBlank()) {
                Text(if (state.authBusy) "正在连接…" else if (register) "注册并开始旅行" else "登录并开始旅行")
            }
            TextButton(onClick = { register = !register; password = "" }, enabled = !state.authBusy) {
                Text(if (register) "已有账号，去登录" else "没有账号，去注册")
            }
        }
    }
}

@Composable
fun ChatContent(state: MuseumState, onDraft: (String) -> Unit, onSend: (String?) -> Unit,
                onStop: () -> Unit, onReload: () -> Unit, onNew: () -> Unit,
                onSession: (ChatSessionInfo) -> Unit, onExhibit: (String?) -> Unit,
                modifier: Modifier = Modifier) {
    var showSessions by remember { mutableStateOf(false) }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(Space.medium)) {
        Text("问阿帛", style = MaterialTheme.typography.headlineLarge)
        Text("${state.audience?.label} · 独立会话", style = MaterialTheme.typography.titleMedium)
        Text("AI 需要联网核验资料；阅读首章不需要联网。", style = MaterialTheme.typography.bodySmall)
        Row(horizontalArrangement = Arrangement.spacedBy(Space.small)) {
            TextButton(onClick = { showSessions = !showSessions }, enabled = !state.chatBusy) { Text("历史会话") }
            TextButton(onClick = onNew, enabled = !state.chatBusy) { Text("新对话") }
            TextButton(onClick = onReload, enabled = !state.chatBusy) { Text("刷新会话") }
        }
        if (showSessions) {
            if (state.sessions.isEmpty()) Text("当前模式暂无历史会话")
            state.sessions.forEach { session ->
                OutlinedButton(onClick = { onSession(session); showSessions = false }, enabled = !state.chatBusy) {
                    Text(session.title)
                }
            }
        }
        Text("当前文物：${FirstChapter.relics.firstOrNull { it.id == state.exhibitId }?.title ?: "博物馆主题"}",
            style = MaterialTheme.typography.bodyMedium)
        if (state.messages.isEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(Space.small)) {
                TextButton(onClick = { onExhibit(null) }, enabled = !state.chatBusy) { Text("主题问答") }
                FirstChapter.relics.forEach { relic ->
                    TextButton(onClick = { onExhibit(relic.id) }, enabled = !state.chatBusy,
                        modifier = Modifier.weight(1f)) { Text(relic.title) }
                }
            }
            MuseumNotice("你可以问用途、比较或故事。资料不足时，阿帛会说明缺口。")
        }
        state.messages.forEachIndexed { index, line -> ChatBubble(line, { onSend(it) },
            enabled = index == state.messages.lastIndex && !state.chatBusy && !state.needsRefresh) }
        if (state.status.isNotBlank()) MuseumNotice(state.status)
        state.error?.let { MuseumNotice(it, error = true) }
        MuseumField(state.draft, onDraft, "想问阿帛什么？", enabled = !state.chatBusy, singleLine = false)
        if (state.chatBusy) MuseumButton(onStop) { Text("停止回复") }
        else MuseumButton(onClick = { onSend(null) }, enabled = state.draft.isNotBlank() && !state.needsRefresh) { Text("发送问题") }
        if (state.needsRefresh) Text("问题已保留。请先刷新核对服务器记录，不会自动重复发送。", style = MaterialTheme.typography.bodySmall)
    }
}

@Preview(showBackground = true)
@Composable
private fun AccountPreview() { MuseumTheme { AccountContent(MuseumState(restoring = false), { _, _, _, _ -> }) } }
