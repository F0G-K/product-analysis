import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';

export function ReportsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-800">报表</h1>
          <p className="text-xs text-gray-400 mt-0.5">需求评估 · 交付质量 · 归因趋势</p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            options={[
              { value: '30d', label: '近 30 天' },
              { value: '90d', label: '近 90 天' },
              { value: 'quarter', label: '本季度' },
            ]}
          />
          <Button variant="secondary">导出</Button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: '评估覆盖率', value: '87%', trend: '+5%', trendUp: true, color: 'primary', target: '≥ 80%' },
          { label: '问题发现率', value: '73%', trend: '+8%', trendUp: true, color: 'teal', target: '≥ 70%' },
          { label: '归因采纳率', value: '78%', trend: '--', trendUp: null, color: 'blue', target: '≥ 70%' },
          { label: '可追溯率', value: '100%', trend: '达标', trendUp: true, color: 'green', target: '100%' },
        ].map((kpi) => (
          <Card key={kpi.label}>
            <div className="text-xs text-gray-500 mb-1">{kpi.label}</div>
            <div className="flex items-end justify-between">
              <span className={`text-3xl font-bold text-${kpi.color}-600`}>{kpi.value}</span>
              {kpi.trendUp !== null && (
                <span className={`text-xs flex items-center gap-1 ${kpi.trendUp ? 'text-green-600' : 'text-gray-400'}`}>
                  {kpi.trendUp ? '↑' : '—'} {kpi.trend}
                </span>
              )}
            </div>
            <div className="text-xs text-gray-400 mt-2">目标 {kpi.target}</div>
            <div className="mt-2 w-full bg-gray-100 rounded-full h-1.5">
              <div className={`bg-${kpi.color}-500 h-1.5 rounded-full`} style={{ width: kpi.value }} />
            </div>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="需求评估趋势">
          <div className="h-48 flex items-end justify-between gap-2 px-2">
            {['W1', 'W2', 'W3', 'W4'].map((week, i) => {
              const h = [70, 75, 85, 87][i];
              return (
                <div key={week} className="flex flex-col items-center gap-1 flex-1">
                  <div className="w-full bg-primary-200 rounded-t" style={{ height: `${h}%` }} />
                  <span className="text-[10px] text-gray-400">{week}</span>
                </div>
              );
            })}
          </div>
          <div className="flex items-center gap-4 mt-3 text-xs justify-center">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-primary-200" /> P0+P1</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-primary-100" /> P2+P3</span>
          </div>
        </Card>

        <Card title="交付质量趋势">
          <div className="h-48 flex items-end justify-between gap-2 px-2">
            {['W1', 'W2', 'W3', 'W4'].map((week, i) => {
              const h = [12, 10, 8, 5][i];
              return (
                <div key={week} className="flex flex-col items-center gap-1 flex-1">
                  <div className="w-full bg-red-200 rounded-t" style={{ height: `${h}%` }} />
                  <span className="text-[10px] text-gray-400">{week}</span>
                </div>
              );
            })}
          </div>
          <div className="flex items-center gap-4 mt-3 text-xs justify-center">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-200" /> 阻断+严重</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-amber-200" /> 一般+提示</span>
          </div>
        </Card>
      </div>
    </div>
  );
}
