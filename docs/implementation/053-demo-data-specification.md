# Especificación de datos de demostración

## Principios

- datos ficticios;
- coherencia entre producto, stock, precio y escenario;
- nombres claramente identificables como demo;
- sin afirmaciones regulatorias no verificadas;
- suficiente variedad para forzar una elección real.

## Organización

```yaml
name: Adega Demo Atlántica
region: Galicia
currency: EUR
default_language: es
demo_only: true
```

## Productos

| SKU | Nombre | Categoría | Unidades/caja | Precio botella | Stock vendible | Ajuste al escenario |
|---|---|---|---:|---:|---:|---|
| ADA-ALB-JOV-2025 | Brétema Albariño 2025 | Albariño joven | 6 | €8.40 | 1,200 | Alto |
| ADA-ALB-LIA-2024 | Luar sobre Lías 2024 | Albariño sobre lías | 6 | €11.90 | 720 | Alto |
| ADA-ESP-BRUT-2023 | Mar de Escuma Brut 2023 | Espumoso | 6 | €13.50 | 180 | Medio |
| ADA-PAR-2023 | Pedra do Norte 2023 | Vino de parcela | 6 | €18.90 | 96 | Bajo por volumen |
| ADA-LIM-2022 | Colección Atlántica 2022 | Edición limitada | 3 | €26.00 | 30 | No apto para volumen |
| ADA-TST-MIX | Estuche Descubrimento | Degustación | 6 | €15.00 | 48 | Muestras |

Los precios son de demostración, sin transporte, impuestos ni aduanas.

## Distribución esperada del escenario principal

Recomendación esperada, no hardcodeada:

- 360 botellas de Brétema Albariño;
- 240 botellas de Luar sobre Lías;
- total: 600 botellas;
- ambas cantidades compatibles con cajas de seis;
- stock suficiente.

La recomendación puede variar si sigue reglas y mantiene coherencia.

## Compradores

### C-001 — Rhein Selection GmbH

- país: Alemania;
- idioma: inglés;
- canal: tiendas especializadas;
- preferencia: vinos blancos atlánticos;
- interacción previa: solicitó fichas técnicas;
- nivel de interés: alto.

### C-002 — Nordic Cellars Demo AB

- país: Suecia;
- idioma: inglés;
- canal: restauración;
- preferencia: referencias premium;
- nivel de interés: medio.

### C-003 — Comprador nuevo

Sin historial. Sirve para probar creación de perfil y memoria inicial.

## Consulta principal

```text
Hello,

We are evaluating Galician Albariño for distribution through specialised wine shops in Germany. For the initial launch, we estimate approximately 600 bottles and would like delivery within the next 60 days.

Please send us your price list and recommend two suitable references. We would also like to receive samples before making a final decision.

Best regards,
Anna Keller
Rhein Selection GmbH
```

## Datos esperados

```yaml
language: en
intent: b2b_purchase_inquiry
market: DE
product_interest: Albariño
estimated_bottles: 600
channel: specialty_retail
target_horizon_days: 60
samples_requested: true
price_list_requested: true
```

## Campos faltantes esperados

- presupuesto;
- dirección de muestras;
- fecha exacta;
- condiciones de entrega;
- requisitos de certificación;
- datos fiscales.

## Escenarios secundarios

1. stock insuficiente para 900 botellas sobre lías;
2. consulta sin volumen;
3. comprador desconocido;
4. mensaje en español;
5. producto solicitado inexistente;
6. ejecución repetida con la misma idempotency key.
