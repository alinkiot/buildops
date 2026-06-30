import { Empty, Card } from 'antd'

export default function Placeholder({ title }: { title: string }) {
  return (
    <Card>
      <Empty
        description={
          <span>
            {title} 模块为 MVP 第二批规划内容，后端数据模型与 API 将在地基四件套稳定后接入。
          </span>
        }
      />
    </Card>
  )
}
