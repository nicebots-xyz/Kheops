## kheops@0.2.0

### Update to Botkit 0.4

Kheops now runs on Botkit 0.4, with typed translations checked at startup and in CI.

### French texts of /informations

The `informations` extension used the `fr-FR` locale, which Discord never sends, so French members saw its English texts. It now uses `fr`.
