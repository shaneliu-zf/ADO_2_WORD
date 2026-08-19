export interface AdoItem {
  id: number
  title: string
  workItemType: string
  state: string
  site: string
  category: string
  issuePriority: string
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
}
