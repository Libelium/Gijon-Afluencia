<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ApiError } from '@/api/http'
import { t } from '@/i18n'
import { formatDateTime } from '@/lib/format'
import { useSessionStore } from '@/stores/session'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import StatTile from '@/components/StatTile.vue'
import UserCreateDialog from '../components/UserCreateDialog.vue'
import {
  deleteUser,
  listUsers,
  sendPasswordEmail,
  setUserEnabled,
  type OrganizationUser,
} from '../api/users'
import { initialsOf, maskEmail, maskName } from '../lib/mask'

const session = useSessionStore()
const organizationId = computed(() => session.user?.organization?.id)

const users = ref<OrganizationUser[]>([])
const loading = ref(false)
const loaded = ref(false)
const error = ref<string | null>(null)
const search = ref('')
const creating = ref(false)
const busy = ref<number | null>(null)

/**
 * Datos personales ocultos por defecto: la pantalla se proyecta, se captura y se usa en puestos
 * compartidos. Mostrarlos es un gesto explicito y se recuerda solo en este navegador.
 */
const MASK_KEY = 'pidgijon.users.masked'
function readMasked(): boolean {
  try {
    return localStorage.getItem(MASK_KEY) !== 'false'
  } catch {
    return true
  }
}
const masked = ref(readMasked())
watch(masked, (value) => {
  try {
    localStorage.setItem(MASK_KEY, String(value))
  } catch {
    // Modo privado: la preferencia vive solo en esta pestana.
  }
})

const headers = computed(() => [
  { title: t('users.col.user'), key: 'name', sortable: true },
  { title: t('users.col.role'), key: 'role', sortable: false },
  { title: t('users.col.status'), key: 'enabled', sortable: true },
  { title: t('users.col.mfa'), key: 'mfa', sortable: true },
  { title: t('users.col.lastActivity'), key: 'lastActivity', sortable: true },
  { title: t('users.col.actions'), key: 'actions', sortable: false, align: 'end' as const },
])

// La busqueda se hace sobre los datos reales aunque se muestren ofuscados: quien administra
// sabe a quien busca, y filtrar por el texto enmascarado no serviria de nada.
const rows = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return users.value
  return users.value.filter(
    (u) => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q),
  )
})

const stats = computed(() => ({
  total: users.value.length,
  active: users.value.filter((u) => u.enabled).length,
  mfa: users.value.filter((u) => u.mfa).length,
}))

const shownName = (u: OrganizationUser) => (masked.value ? maskName(u.name) : u.name)
const shownEmail = (u: OrganizationUser) => (masked.value ? maskEmail(u.email) : u.email)

function roleLabel(u: OrganizationUser): string {
  if (u.isOrganizationAdmin) return t('users.role.orgAdmin')
  if (u.roles.includes('super_admin')) return t('users.role.superAdmin')
  if (u.roles.includes('qc_admin')) return t('users.role.qcAdmin')
  return t('users.role.member')
}

const isSelf = (u: OrganizationUser) => u.id === session.user?.id

async function load() {
  if (!organizationId.value) return
  loading.value = true
  error.value = null
  try {
    users.value = await listUsers(organizationId.value)
    loaded.value = true
  } catch (e) {
    error.value =
      e instanceof ApiError && e.kind === 'forbidden' ? t('users.forbidden') : t('users.loadFailed')
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(organizationId, load)

const snack = reactive({ open: false, color: 'success', text: '' })
function notify(text: string, color = 'success') {
  snack.text = text
  snack.color = color
  snack.open = true
}

function onCreated(user: OrganizationUser, invitationSent: boolean) {
  users.value = [...users.value, user].sort((a, b) => a.name.localeCompare(b.name))
  notify(
    invitationSent ? t('users.create.done') : t('users.create.doneNoMail'),
    invitationSent ? 'success' : 'warning',
  )
}

// Desactivar y eliminar piden confirmacion; activar y reenviar el correo no, se deshacen solos.
const confirm = reactive({
  open: false,
  action: 'disable' as 'disable' | 'delete',
  user: null as OrganizationUser | null,
})

function ask(action: 'disable' | 'delete', user: OrganizationUser) {
  confirm.action = action
  confirm.user = user
  confirm.open = true
}

async function run<T>(user: OrganizationUser, task: () => Promise<T>, ok: string, ko: string) {
  busy.value = user.id
  try {
    const result = await task()
    notify(ok)
    return result
  } catch {
    notify(ko, 'error')
    return undefined
  } finally {
    busy.value = null
  }
}

async function toggleEnabled(user: OrganizationUser, enabled: boolean) {
  const orgId = organizationId.value
  if (!orgId) return
  const updated = await run(
    user,
    () => setUserEnabled(orgId, user.id, enabled),
    t(enabled ? 'users.enable.done' : 'users.disable.done'),
    t('users.actionFailed'),
  )
  if (updated) users.value = users.value.map((u) => (u.id === updated.id ? updated : u))
}

async function resendPassword(user: OrganizationUser) {
  const orgId = organizationId.value
  if (!orgId) return
  await run(
    user,
    () => sendPasswordEmail(orgId, user.id),
    t('users.password.done'),
    t('users.password.failed'),
  )
}

async function confirmAction() {
  const user = confirm.user
  const orgId = organizationId.value
  confirm.open = false
  if (!user || !orgId) return

  if (confirm.action === 'disable') {
    await toggleEnabled(user, false)
    return
  }

  const removed = await run(
    user,
    () => deleteUser(orgId, user.id).then(() => true),
    t('users.delete.done'),
    t('users.actionFailed'),
  )
  if (removed) users.value = users.value.filter((u) => u.id !== user.id)
}
</script>

<template>
  <div>
    <PageHeader
      :title="t('users.title')"
      :subtitle="t('users.subtitle')"
      :count="loaded ? t('users.count', { count: stats.total }) : undefined"
      icon="mdi-account-group-outline"
    >
      <template #actions>
        <VBtn
          color="primary"
          prepend-icon="mdi-account-plus-outline"
          :disabled="!loaded"
          @click="creating = true"
        >
          {{ t('users.new') }}
        </VBtn>
      </template>
    </PageHeader>

    <div v-if="loaded" class="d-flex flex-wrap ga-4 mb-6">
      <StatTile :label="t('users.kpi.total')" :value="stats.total" icon="mdi-account-multiple-outline" />
      <StatTile :label="t('users.kpi.active')" :value="stats.active" icon="mdi-account-check-outline" />
      <StatTile :label="t('users.kpi.mfa')" :value="stats.mfa" icon="mdi-shield-lock-outline" />
    </div>

    <VCard>
      <div class="d-flex flex-wrap align-center ga-4 pa-4">
        <VTextField
          v-model="search"
          :label="t('users.search')"
          prepend-inner-icon="mdi-magnify"
          clearable
          max-width="380"
          class="flex-grow-1"
        />
        <VSpacer />
        <VSwitch
          v-model="masked"
          :label="t('users.mask')"
          color="primary"
          inset
          hide-details
          class="flex-grow-0"
        />
      </div>
      <p class="text-caption text-medium-emphasis px-4 pb-3 mt-n2">
        {{ masked ? t('users.mask.on') : t('users.mask.off') }}
      </p>

      <VDivider />

      <StateBlock
        :loading="loading && !loaded"
        :error="error"
        :empty="loaded && rows.length === 0"
        :empty-text="search ? t('users.emptySearch') : t('users.empty')"
        empty-icon="mdi-account-off-outline"
        skeleton="table"
        @retry="load"
      >
        <VDataTable
          :headers="headers"
          :items="rows"
          :loading="loading"
          :loading-text="t('common.loading')"
          item-value="id"
          :items-per-page="25"
          :items-per-page-text="t('common.rowsPerPage')"
        >
          <template #[`item.name`]="{ item }">
            <div class="d-flex align-center ga-3 py-2 min-w-0">
              <VAvatar color="primary" variant="tonal" size="36">
                <span class="text-caption font-weight-bold">{{ initialsOf(item.name, masked) }}</span>
              </VAvatar>
              <div class="min-w-0">
                <div class="text-body-2 font-weight-medium text-truncate">
                  {{ shownName(item) }}
                  <span v-if="isSelf(item)" class="text-caption text-medium-emphasis">
                    ({{ t('users.you') }})
                  </span>
                </div>
                <div class="text-caption text-medium-emphasis text-truncate">
                  {{ shownEmail(item) }}
                </div>
              </div>
            </div>
          </template>

          <template #[`item.role`]="{ item }">
            <span class="text-body-2">{{ roleLabel(item) }}</span>
          </template>

          <!-- Texto e icono, no solo color (WCAG 1.4.1). -->
          <template #[`item.enabled`]="{ item }">
            <VChip
              :color="item.enabled ? 'success' : 'default'"
              :prepend-icon="item.enabled ? 'mdi-check-circle-outline' : 'mdi-cancel'"
              size="small"
              variant="tonal"
            >
              {{ item.enabled ? t('users.status.active') : t('users.status.disabled') }}
            </VChip>
          </template>

          <template #[`item.mfa`]="{ item }">
            <span class="d-inline-flex align-center ga-1 text-body-2">
              <VIcon
                :icon="item.mfa ? 'mdi-shield-check-outline' : 'mdi-shield-off-outline'"
                :color="item.mfa ? 'success' : undefined"
                size="18"
              />
              {{ item.mfa ? t('users.mfa.on') : t('users.mfa.off') }}
            </span>
          </template>

          <template #[`item.lastActivity`]="{ item }">
            <span class="text-body-2 text-medium-emphasis">
              {{ item.lastActivity ? formatDateTime(item.lastActivity, session.timeZone) : '—' }}
            </span>
          </template>

          <template #[`item.actions`]="{ item }">
            <VMenu location="bottom end">
              <template #activator="{ props: menu }">
                <VBtn
                  v-bind="menu"
                  icon="mdi-dots-vertical"
                  variant="text"
                  density="comfortable"
                  :loading="busy === item.id"
                  :aria-label="t('users.actions', { name: shownName(item) })"
                />
              </template>
              <VList density="compact">
                <VListItem
                  prepend-icon="mdi-email-lock-outline"
                  :title="t('users.password.action')"
                  :disabled="!item.enabled"
                  @click="resendPassword(item)"
                />
                <VListItem
                  v-if="item.enabled"
                  prepend-icon="mdi-account-cancel-outline"
                  :title="t('users.disable.action')"
                  :disabled="isSelf(item)"
                  @click="ask('disable', item)"
                />
                <VListItem
                  v-else
                  prepend-icon="mdi-account-check-outline"
                  :title="t('users.enable.action')"
                  @click="toggleEnabled(item, true)"
                />
                <VDivider class="my-1" />
                <VListItem
                  prepend-icon="mdi-delete-outline"
                  :title="t('users.delete.action')"
                  base-color="error"
                  :disabled="isSelf(item) || item.isOrganizationAdmin"
                  @click="ask('delete', item)"
                />
              </VList>
            </VMenu>
          </template>
        </VDataTable>
      </StateBlock>
    </VCard>

    <UserCreateDialog
      v-if="organizationId"
      v-model="creating"
      :organization-id="organizationId"
      @created="onCreated"
    />

    <VDialog v-model="confirm.open" max-width="460">
      <VCard :title="t(confirm.action === 'delete' ? 'users.delete.title' : 'users.disable.title')">
        <VCardText>
          {{
            t(confirm.action === 'delete' ? 'users.delete.text' : 'users.disable.text', {
              name: confirm.user ? shownName(confirm.user) : '',
            })
          }}
        </VCardText>
        <VCardActions class="px-6 pb-4">
          <VSpacer />
          <VBtn variant="text" @click="confirm.open = false">{{ t('common.cancel') }}</VBtn>
          <VBtn
            :color="confirm.action === 'delete' ? 'error' : 'primary'"
            variant="flat"
            @click="confirmAction"
          >
            {{ t(confirm.action === 'delete' ? 'users.delete.confirm' : 'users.disable.confirm') }}
          </VBtn>
        </VCardActions>
      </VCard>
    </VDialog>

    <!-- Sin cierre automatico (WCAG 2.2.1), como el resto de avisos de la aplicacion. -->
    <VSnackbar v-model="snack.open" :color="snack.color" :timeout="-1" location="bottom">
      <div :role="snack.color === 'success' ? 'status' : 'alert'">{{ snack.text }}</div>
      <template #actions>
        <VBtn variant="text" @click="snack.open = false">{{ t('common.close') }}</VBtn>
      </template>
    </VSnackbar>
  </div>
</template>
