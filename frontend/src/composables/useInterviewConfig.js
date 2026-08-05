import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/index.js'
import { TYPE_TO_PROFILE } from '@/data/interview.js'

export function createConfiguredSession(client, {
  projectId,
  profileId,
  mode,
  resumeId,
  githubRepoIds,
}) {
  if (projectId) {
    return client.createProjectSession(projectId, {
      profile_id: profileId,
      mode,
      github_repo_ids: githubRepoIds,
    })
  }
  return client.createSession({ profileId, mode, resumeId, githubRepoIds })
}

export function useInterviewConfig() {
  const router = useRouter()
  const route = useRoute()

  const resumes = ref([])
  const resumesLoading = ref(false)
  const githubRepos = ref([])
  const reposLoading = ref(false)
  const starting = ref(false)
  const startError = ref('')

  const interviewTypes = [
    { id: 'technical', label: '技术面试', description: '深入技术细节和项目实现' },
    { id: 'behavioral', label: '行为面试', description: '软技能、团队协作、问题解决' },
    { id: 'comprehensive', label: '综合面试', description: '技术能力和行为表现结合' },
  ]

  const selectedResume = ref(null)
  const selectedType = ref('comprehensive')
  const selectedMode = ref('text')
  const selectedGithubRepos = ref([])

  const isConfigValid = computed(() => selectedType.value !== null)

  async function loadGithubRepos() {
    reposLoading.value = true
    try {
      const data = await api.getGithubRepos()
      githubRepos.value = data
    } catch (e) {
      console.error('Failed to load GitHub repos:', e)
      githubRepos.value = []
    } finally {
      reposLoading.value = false
    }
  }

  async function loadResumes() {
    resumesLoading.value = true
    try {
      const data = await api.getResumes()
      resumes.value = data
    } catch (e) {
      console.error('Failed to load resumes:', e)
      resumes.value = []
    } finally {
      resumesLoading.value = false
    }
  }

  onMounted(() => {
    loadResumes()
    loadGithubRepos()
  })

  async function handleStartInterview() {
    if (!isConfigValid.value || starting.value) return
    starting.value = true
    startError.value = ''

    try {
      const profileId = TYPE_TO_PROFILE[selectedType.value]
      const projectId = typeof route.query.projectId === 'string' ? route.query.projectId : null
      const result = await createConfiguredSession(api, {
        projectId,
        profileId,
        mode: selectedMode.value,
        resumeId: selectedResume.value,
        githubRepoIds: selectedGithubRepos.value,
      })
      router.push(`/interview/${result.session_id}?type=${selectedType.value}&projectId=${projectId || ''}`)
    } catch (e) {
      console.error('Failed to create session:', e)
      startError.value = e.message || '创建面试会话失败，请重试'
    } finally {
      starting.value = false
    }
  }

  function handleGoToUpload() {
    router.push('/analysis/resume')
  }

  function handleGoToAnalysis() {
    router.push('/analysis/github')
  }

  return {
    resumes,
    resumesLoading,
    githubRepos,
    reposLoading,
    selectedGithubRepos,
    interviewTypes,
    selectedResume,
    selectedType,
    selectedMode,
    isConfigValid,
    starting,
    startError,
    handleStartInterview,
    handleGoToUpload,
    handleGoToAnalysis,
    loadResumes,
    loadGithubRepos,
  }
}
