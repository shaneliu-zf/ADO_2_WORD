export interface AdoItem {
  id: number
  title: string
  workItemType: string
  state: string
  site: string
  category: string
  issuePriority: string
  redmineId: string
  assignedTo: string
  createdBy: string
  saBy: string
  engineerBy: string
  testerBy: string
  createdDate: string
  fetched: boolean
  grouped: boolean
  hasReport: boolean
  hasJson: boolean
  hasHtml: boolean
  lastUpdated: string
}

export interface AdoTableRow extends AdoItem {
  groupKey: number
  groupSize: number
  groupIds: number[]
  redmineId: string
  isGroupHead: boolean
  groupHasReport: boolean
  relationKind: 'related' | 'solo' | 'unknown'
}

export interface TestItem {
  no: number
  item_name: string
  test_data: string[]
  expected_result: string
  test_result: string
}

export interface Group {
  ids: number[]
  primary_id: number
  redmine_id: string
}

export interface AppConfig {
  organization: string
  project: string
  pat: string
  ado_base_url: string
  bob_api_key: string
}

export interface PipelineSession {
  ids: number[]
  listedIds: number[]
  currentStep: number
  reachedStep: number
}

export interface TestStep {
  no: number
  description: string
  images: string[]
}

export interface CommitEntry {
  sha: string
  sha_short: string
  message: string
  author: string
  date: string
  url: string
  ado_id?: number
}

export interface Report {
  ado_id: number
  ado_ids: number[]
  redmine_id: string
  ado_subject: string
  test_environment: string
  site: string
  version: string
  test_date: string
  tester: string
  reviewer: string
  test_items: TestItem[]
  test_steps: TestStep[]
  commits?: CommitEntry[]
}
