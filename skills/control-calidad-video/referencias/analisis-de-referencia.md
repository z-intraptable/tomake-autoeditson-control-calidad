# Ficha de análisis de una referencia

Para entender por qué funciona una pieza ajena (o la de un competidor) y qué hace falta para igualarla. Correr primero `scripts/qc_video.py` sobre la referencia: da los cortes, el plano medio y las hojas.

```
REFERENCIA:     <marca / título / link>
TÉCNICO:        <duración> · <resolución> · <fps> · <loudness> LUFS
PLANOS:         <cantidad> · plano medio <s> · el más largo <s> en <timecode>
GANCHO (0-2 s): <qué pasa cuadro a cuadro>
TÉCNICAS:       <timecode> — <técnica> (una por línea)
TIPOGRAFÍA:     <fuentes, tamaño, cómo entra y sale>
CAPAS:          <cuántas a la vez en el plano más denso>
TRANSICIONES:   <tipos y duración>
COLOR:          <paleta, contraste, acabado>
SONIDO:         <género, SFX, silencios, voz>
CIERRE Y CTA:   <cómo termina, cuánto dura el packshot>
```

## Después de varias fichas
1. **Patrones comunes:** lo que se repite en 3 o más referencias es la norma del rubro.
2. **Brecha:** para cada técnica, ¿la podemos hacer hoy? Sí / parcial / no, y cómo se implementaría.
3. **Lo que nadie hace:** el hueco donde una pieza propia se puede diferenciar.

## Comparar pieza contra referencia
- Mismo número de cuadros en las dos hojas, misma distancia entre cuadros.
- Ponerlas una arriba de la otra y comparar cuadro a cuadro: foco, densidad, color, texto.
- Reportar en una tabla: eje · referencia · pieza · qué cambiar.
