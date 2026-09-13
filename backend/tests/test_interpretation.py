"""Pruebas sin red de las interpretaciones y compras futuras."""
import asyncio
import os
import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

os.environ.setdefault('GEMINI_API_KEYS', 'test-key')
import agent


class InterpretationTests(unittest.TestCase):
    def test_future_purchase_uses_current_data_and_original_question(self):
        question = '¿Puedo comprar una laptop el próximo mes?'
        router = AsyncMock(return_value={'intencion': 'diagnostico_financiero',
            'evaluar_compra': True, 'fecha_inicio': '2099-01-01', 'fecha_fin': '2099-01-31'})
        handler = AsyncMock(return_value={'ok': True})
        with patch.object(agent, '_clasificar_intencion', router), patch.object(agent, '_handler_diagnostico_financiero', handler):
            asyncio.run(agent._responder_consulta(question, 'test'))
        handler.assert_awaited_once_with('test', date.today().replace(day=1), date.today(), question, True)

    def test_invalid_interpretation_explains_failure(self):
        for response in ({'mensaje': ''}, {}, None):
            with patch.object(agent, '_generar_json', AsyncMock(return_value=response)):
                text = asyncio.run(agent._interpretar('¿Me alcanza?', {}, 'Necesito tu saldo.'))
            self.assertIn('Necesito tu saldo.', text)
            self.assertIn('No pude generar', text)

    def test_question_and_data_reach_model(self):
        generate = AsyncMock(return_value={'mensaje': 'Necesito tu saldo disponible.'})
        with patch.object(agent, '_generar_json', generate):
            result = asyncio.run(agent._interpretar('¿Me alcanza para $500?', {'total_gastado': 100}, 'fallback'))
        self.assertEqual(result, 'Necesito tu saldo disponible.')
        prompt = generate.call_args.args[0]
        self.assertIn('¿Me alcanza para $500?', prompt)
        self.assertIn('"total_gastado": 100', prompt)

    def test_model_unavailable_keeps_fallback(self):
        with patch.object(agent, '_generar_json', AsyncMock(side_effect=RuntimeError('quota'))):
            result = asyncio.run(agent._interpretar('consulta', {}, 'Datos disponibles.'))
        self.assertIn('Datos disponibles.', result)


if __name__ == '__main__':
    unittest.main()
