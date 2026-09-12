import test from 'node:test';
import assert from 'node:assert/strict';
import { parseEnvelope } from '../src/lib/parseEnvelope.ts';
import { mockOverview, mockMessage, mockCategoryDetail } from '../src/lib/mockAgent.ts';
import { validProps } from '../src/components/a2ui/validation.ts';
import { validTransactionProps } from '../src/lib/validateTransactions.ts';

test('sample JSON survives the reception boundary and includes the new catalog', () => {
  const result = parseEnvelope(JSON.stringify(mockOverview('test')), 'test');
  assert.deepEqual(result.components.map(c => c.type), ['progress', 'risk_indicator', 'category_badge', 'pie_chart', 'action_button']);
  const names = { progress: 'Progress', risk_indicator: 'RiskIndicator', category_badge: 'CategoryBadge', pie_chart: 'PieChart', action_button: 'ActionButton' };
  for (const component of result.components) assert.equal(validProps(names[component.type], component.props), true);
});

test('rejects broken JSON, wrong conversations, versions, actions, and duplicate IDs', () => {
  assert.throws(() => parseEnvelope('{', 'test'), /JSON/);
  const envelope = mockOverview('test');
  for (const value of [null, [], {}, { ...envelope, version: '2.0' }, { ...envelope, conversation_id: 'other' },
    { ...envelope, components: [envelope.components[0], envelope.components[0]] },
    { ...envelope, components: [{ id: 'x', type: 'progress', props: {}, actions: [{}] }] }]) {
    assert.throws(() => parseEnvelope(value, 'test'));
  }
});

test('supports empty results, alternate charts, details and recoverable demo errors', () => {
  assert.equal(parseEnvelope(JSON.stringify(mockMessage('test', 'demo vacío')), 'test').components.length, 0);
  assert.ok(mockMessage('test', 'barras').components.some(c => c.type === 'bar_chart'));
  const detail = parseEnvelope(JSON.stringify(mockCategoryDetail('test', 'despensa')), 'test').components[0];
  assert.equal(validTransactionProps(detail.props), true);
  assert.equal(detail.actions[0].id, 'back_to_overview');
  assert.throws(() => mockMessage('test', 'demo error'), /simulado/);
  assert.throws(() => parseEnvelope(mockMessage('test', 'demo inválido'), 'test'));
});

test('invalid props cannot reach charts or transaction rendering', () => {
  assert.equal(validProps('Progress', { label: 'Budget', value: Infinity, max: 100 }), false);
  assert.equal(validProps('PieChart', { categories: null }), false);
  assert.equal(validTransactionProps({ period: {}, transactions: [] }), false);
  const props = mockCategoryDetail('test', 'despensa').components[0].props;
  assert.equal(validTransactionProps({ ...props, transactions: [{ id: 'bad', amount: '100' }] }), false);
});

test('both overview charts include inline transactions without remote category actions', () => {
  for (const type of ['pie_chart', 'bar_chart']) {
    const envelope = parseEnvelope(JSON.stringify(mockOverview('test', type)), 'test');
    const overview = envelope.components.find(component => component.id === 'spending_overview');
    assert.equal(overview.actions, undefined);
    for (const category of overview.props.categories) {
      assert.ok(Array.isArray(category.transactions));
      assert.equal(validTransactionProps({ category, period: overview.props.period, total: category.total, transactions: category.transactions }), true);
    }
    assert.equal(overview.props.categories[0].transactions[0].description, 'Walmart');
  }
});
