<template>
  <div class="welcome">
    <HeaderBar />
    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="params-card" shadow="never">
            <div class="operation-header">
              <h2 class="page-title">{{ $t('serverSideManager.pageTitle') }}</h2>
            </div>
            <el-card class="museum-device-card" shadow="never">
              <div class="museum-device-heading">
                <div>
                  <h3>智博导览设备连接</h3>
                  <p>设备通过 OTA 获取这里的 WebSocket 地址。切换到本地智博导览服务后，设备和运行服务的电脑必须在同一局域网。</p>
                </div>
                <el-tag :type="websocketParam ? 'success' : 'warning'">
                  {{ websocketParam ? '已读取 server.websocket' : '未读取配置' }}
                </el-tag>
              </div>
              <el-form label-position="top" class="museum-device-form" @submit.native.prevent="saveWebsocketParam">
                <el-form-item label="设备 WebSocket 地址">
                  <el-input
                    v-model="websocketDraft"
                    :disabled="websocketLoading || websocketSaving"
                    placeholder="ws://局域网IP:8011/xiaozhi/v1/"
                    clearable
                  />
                </el-form-item>
                <div class="museum-device-actions">
                  <el-button type="primary" :loading="websocketSaving" @click="saveWebsocketParam">
                    保存连接地址
                  </el-button>
                  <el-button :disabled="websocketLoading || websocketSaving" @click="resetWebsocketDraft">
                    恢复已保存地址
                  </el-button>
                  <el-button :disabled="websocketLoading" @click="fetchWebsocketParam">
                    刷新配置
                  </el-button>
                </div>
              </el-form>
              <div class="museum-device-hint">
                本地演示地址格式：<code>ws://电脑局域网IP:8011/xiaozhi/v1/</code>。不能填写 localhost 或 127.0.0.1，设备无法访问电脑本机回环地址；如需回到官方服务，恢复原来的官方 WebSocket 地址即可。
              </div>
              <el-alert
                v-if="websocketMessage"
                class="museum-device-message"
                :title="websocketMessage"
                :type="websocketMessageType || 'info'"
                :closable="false"
                show-icon
              />
            </el-card>
            <el-card class="server-list-card">
              <div v-for="(item, index) in paramsList" :key="index" class="server-list" v-loading="loading">
                <div class="server-card">
                  <div class="server-info">
                    <span class="server-label">{{ $t('serverSideManager.wsAddress') }}</span>
                    <span class="server-value">{{ item.address }}</span>
                  </div>
                  <el-button class="copy-button" type="text" size="small" @click="copyAddress(item.address)">{{ $t('common.copyAddress') }}</el-button>
                </div>
                <el-divider />
                <div class="header-actions">
                  <CustomButton icon="el-icon-refresh-right" size="small" @click="emitAction(item, actionMap.restart)">{{
                    $t('serverSideManager.restart') }}</CustomButton>
                  <CustomButton icon="el-icon-setting" size="small" type="confirm" @click="emitAction(item, actionMap.update_config)">
                    {{ $t('serverSideManager.updateConfig') }}
                  </CustomButton>
                </div>
                <el-empty v-if="paramsList.length === 0 && !loading" :description="$t('common.noData')"></el-empty>
              </div>
            </el-card>
          </el-card>
        </div>
      </div>
    </div>
    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import Api from "@/apis/api";
import CustomButton from "@/components/CustomButton.vue";
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";

export default {
  components: { HeaderBar, VersionFooter, CustomButton },
  data() {
    return {
      paramsList: [],
      loading: false,
      websocketParam: null,
      websocketDraft: "",
      websocketLoading: false,
      websocketSaving: false,
      websocketMessage: "",
      websocketMessageType: "",
    };
  },
  created() {
    this.fetchParams();
    this.fetchWebsocketParam();
  },
  computed: {
    actionMap() {
      return {
        restart: {
          value: 'restart',
          title: this.$t('serverSideManager.restartServer'),
          message: this.$t('serverSideManager.confirmRestart'),
          confirmText: this.$t('serverSideManager.restart'),
        },
        update_config: {
          value: 'update_config',
          title: this.$t('serverSideManager.updateConfigTitle'),
          message: this.$t('serverSideManager.confirmUpdateConfig'),
          confirmText: this.$t('serverSideManager.updateConfig'),
        }
      };
    }
  },
  methods: {
    fetchParams() {
      this.loading = true;
      Api.admin.getWsServerList(
        {},
        ({ data }) => {
          this.loading = false;
          if (data.code === 0) {
            this.paramsList = data.data.map(item => ({ address: item }));
          } else {
            this.$message.error({
              message: data.msg || this.$t('serverSideManager.getServerListFailed'),
              showClose: true
            });
          }
        }
      );
    },
    fetchWebsocketParam() {
      this.websocketLoading = true;
      Api.admin.getParamsList(
        { page: 1, limit: 100, paramCode: "server.websocket" },
        ({ data }) => {
          this.websocketLoading = false;
          if (data.code !== 0) {
            this.websocketMessageType = "warning";
            this.websocketMessage = data.msg || "读取设备 WebSocket 配置失败，请到参数管理查看 server.websocket。";
            return;
          }
          const list = data.data && Array.isArray(data.data.list) ? data.data.list : [];
          this.websocketParam = list.find(item => item.paramCode === "server.websocket") || null;
          this.websocketDraft = this.websocketParam ? (this.websocketParam.paramValue || "") : "";
          if (!this.websocketParam) {
            this.websocketMessageType = "warning";
            this.websocketMessage = "未找到 server.websocket 参数，请先在参数管理中初始化服务端配置。";
          }
        },
        () => {
          this.websocketLoading = false;
          this.websocketMessageType = "error";
          this.websocketMessage = "读取设备 WebSocket 配置失败，请检查管理端服务。";
        }
      );
    },
    resetWebsocketDraft() {
      this.websocketDraft = this.websocketParam ? (this.websocketParam.paramValue || "") : "";
      this.websocketMessage = "";
      this.websocketMessageType = "";
    },
    validateWebsocketDraft(value) {
      const urls = value.split(";").map(item => item.trim()).filter(Boolean);
      if (urls.length === 0) {
        return "请输入至少一个 WebSocket 地址。";
      }
      const pattern = /^wss?:\/\/[^\s;]+$/i;
      for (const url of urls) {
        if (url.includes("localhost") || url.includes("127.0.0.1")) {
          return "设备地址不能使用 localhost 或 127.0.0.1，请填写电脑的局域网 IP。";
        }
        if (!pattern.test(url)) {
          return `WebSocket 地址格式不正确：${url}`;
        }
      }
      return "";
    },
    saveWebsocketParam() {
      const value = (this.websocketDraft || "").split(";").map(item => item.trim()).filter(Boolean).join(";");
      const validationMessage = this.validateWebsocketDraft(value);
      if (validationMessage) {
        this.websocketMessageType = "warning";
        this.websocketMessage = validationMessage;
        return;
      }
      if (!this.websocketParam || !this.websocketParam.id) {
        this.websocketMessageType = "warning";
        this.websocketMessage = "未找到 server.websocket 参数，请先到参数管理初始化。";
        return;
      }
      if (value === (this.websocketParam.paramValue || "").trim()) {
        this.websocketMessageType = "info";
        this.websocketMessage = "连接地址没有变化。";
        return;
      }

      this.websocketSaving = true;
      Api.admin.updateParam(
        {
          id: this.websocketParam.id,
          paramCode: this.websocketParam.paramCode,
          paramValue: value,
          valueType: this.websocketParam.valueType || "string",
          remark: this.websocketParam.remark || "设备 WebSocket 地址，多个用;分隔"
        },
        ({ data }) => {
          this.websocketSaving = false;
          if (data.code !== 0) {
            this.websocketMessageType = "error";
            this.websocketMessage = data.msg || "保存 WebSocket 地址失败。";
            return;
          }
          this.websocketParam.paramValue = value;
          this.websocketDraft = value;
          this.websocketMessageType = "success";
          this.websocketMessage = "连接地址已保存。请让设备重新请求 OTA；如本地服务已启用管理接口，再点击下方服务端的“更新配置”。";
          this.fetchParams();
          this.fetchWebsocketParam();
        },
        () => {
          this.websocketSaving = false;
          this.websocketMessageType = "error";
          this.websocketMessage = "保存 WebSocket 地址失败，请检查当前账号权限。";
        }
      );
    },
    emitAction(rowItem, actionItem) {
      if (actionItem === undefined || rowItem.address === undefined) {
        return;
      }
      this.$confirm(actionItem.message, actionItem.title, {
        confirmButtonText: actionItem.confirmText,
        cancelButtonText: this.$t('common.cancel')
      }).then(() => {
        Api.admin.sendWsServerAction({
          targetWs: rowItem.address,
          action: actionItem.value
        }, ({ data }) => {
          if (data.code !== 0) {
            this.$message.error({
              message: data.msg || this.$t('serverSideManager.operationFailed'),
              showClose: true
            });
            return;
          }
          this.$message.success({
            message: actionItem.value === 'restart' ? this.$t('serverSideManager.restartSuccess') : this.$t('serverSideManager.updateConfigSuccess'),
            showClose: true
          })
        })
      })
    },
    copyAddress(address) {
      navigator.clipboard.writeText(address).then(() => {
        this.$message.success(this.$t('common.copySuccess'));
      }).catch(() => {
        this.$message.error(this.$t('common.copyFailed'));
      });
    }
  }
};
</script>

<style lang="scss" scoped>
.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  position: relative;
  flex-direction: column;
  background-size: cover;
  background: linear-gradient(to bottom right, #f8f5ef, #f7f0e4, #efe1ca) center;
  -webkit-background-size: cover;
  -o-background-size: cover;
  overflow: hidden;
}

.main-wrapper {
  height: calc(100vh - 63px - 35px);
  padding: 20px 22px 0;
  position: relative;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.page-title {
  font-weight: 500;
  font-size: 24px;
  margin: 0;
}

.content-panel {
  display: flex;
  overflow: hidden;
  height: 100%;
  border-radius: 15px;
  background: transparent;
  border: 1px solid #fff;
}

.content-area {
  flex: 1;
  height: 100%;
  min-width: 600px;
  overflow: auto;
  background-color: white;
  display: flex;
  flex-direction: column;
}

.params-card {
  background: white;
  flex: 1;
  display: flex;
  flex-direction: column;
  border: none;
  box-shadow: none;
  overflow: hidden;

  ::v-deep .el-card__body {
    padding: 14px 20px;
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
  }
}

.museum-device-card {
  margin: 0 0 16px;
  border: 1px solid #dbe7ff;
  border-radius: 12px;
  background: linear-gradient(135deg, #f7faff 0%, #ffffff 100%);

  ::v-deep .el-card__body {
    padding: 18px 20px;
  }
}

.museum-device-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;

  h3 {
    margin: 0;
    color: #1e3a8a;
    font-size: 18px;
  }

  p {
    margin: 8px 0 0;
    color: #64748b;
    font-size: 13px;
    line-height: 1.6;
  }
}

.museum-device-form {
  margin-top: 14px;

  ::v-deep .el-form-item {
    margin-bottom: 10px;
  }

  ::v-deep .el-form-item__label {
    padding-bottom: 4px;
    color: #475569;
    font-weight: 500;
  }
}

.museum-device-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.museum-device-hint {
  margin-top: 12px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.7;

  code {
    padding: 2px 5px;
    color: #1d4ed8;
    background: #eef4ff;
    border-radius: 4px;
  }
}

.museum-device-message {
  margin-top: 12px;
}

.server-list {
  padding: 16px 20px;
  border-radius: 10px;
  box-shadow: 0 0 8px #ececec;
}

.server-list-card {
  flex: 1;
  border: none;
  border-radius: 8px;
  box-shadow: none;

  ::v-deep .el-card__body {
    gap: 20px;
    overflow: auto;
    padding: 16px;
    height: 100%;
    box-sizing: border-box;
  }

  ::v-deep .el-divider {
    margin: 16px 0 !important;
    background: #ecf2fb !important;
  }
}

.header-actions {
  display: flex;
  justify-content: flex-end;
}

.operation-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 16px 0;
  box-sizing: border-box;
}

.server-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-radius: 10px;
  background: rgba(239, 243, 252, 0.4);
  border: 1px solid #ecf2fb;
}

.server-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.server-label {
  font-size: 16px;
  font-weight: 500;
}

.server-value {
  margin-top: 10px;
  font-size: 14px;
}

.server-actions {
  display: flex;
  gap: 8px;
}
.copy-button {
  font-size: 14px;
  color: var(--museum-primary);
}
</style>
