<template>
  <div class="brand-lockup" :class="`brand-lockup--${size}`">
    <img src="@/assets/brand/zhibo-mark.png" alt="" class="brand-lockup__mark" />
    <span class="brand-lockup__copy">
      <strong>智博导览</strong>
      <small>SMART MUSEUM GUIDE</small>
    </span>
  </div>
</template>

<script>
export default {
  name: "BrandLockup",
  props: {
    size: {
      type: String,
      default: "default",
    },
  },
};
</script>

<style scoped>
.brand-lockup {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--museum-text);
}

.brand-lockup__mark {
  width: 46px;
  height: 46px;
  object-fit: contain;
}

.brand-lockup__copy {
  display: flex;
  flex-direction: column;
  line-height: 1;
}

.brand-lockup__copy strong {
  font-size: 21px;
  font-weight: 750;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.brand-lockup__copy small {
  margin-top: 6px;
  color: var(--museum-primary-hover);
  font-size: 8px;
  font-weight: 650;
  letter-spacing: 0.18em;
  white-space: nowrap;
}

.brand-lockup--large {
  gap: 14px;
}

.brand-lockup--large .brand-lockup__mark {
  width: 64px;
  height: 64px;
}

.brand-lockup--large .brand-lockup__copy strong {
  font-size: 28px;
}

.brand-lockup--large .brand-lockup__copy small {
  margin-top: 8px;
  font-size: 10px;
}
</style>
