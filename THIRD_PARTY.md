# Fremdanteile

Der Großteil des Repos ist eigene Arbeit. Diese Teile stammen ganz oder in Teilen aus anderen
Open-Source-Projekten; die jeweilige Lizenz gilt für den übernommenen Anteil.

| Teil im Repo | Herkunft | Lizenz | Art der Übernahme |
|---|---|---|---|
| `skills/leanrea/` | [aicodeking/leanrea](https://github.com/aicodeking/leanrea) (Commit `09ba4aa0217f`) | MIT, Text in `skills/leanrea/LICENSE` | Skill unverändert, ergänzt um einen Abschnitt „Lokal" |
| `skills/design-html/vendor/pretext.js` | [chenglou/pretext](https://github.com/chenglou/pretext) | MIT | Bibliothek unverändert gebündelt |
| `skills/design-html`, `design-shotgun`, `office-hours`, `plan-ceo-review`, `investigate`, `cso`, `full-audit`, `review`, `ui-critique` (Teile) | [garrytan/gstack](https://github.com/garrytan/gstack) | MIT | Abläufe portiert und umgeschrieben („gstack-Port") |
| Techniken in `investigate`, `review`, `gate`, `skill-create`, `office-hours`, `plan-ceo-review`, `branch-finish`, `deploy-preflight`, `test-run` | [obra/superpowers](https://github.com/obra/superpowers) v6.1.1 | MIT | einzelne Techniken übernommen und markiert („geerntet aus superpowers") |
| `hooks/caveman-*` (6 Dateien) | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | MIT laut LICENSE der verwendeten Version (das Upstream-Repo steht inzwischen unter Apache-2.0) | Plugin-Hooks unverändert |

Nicht enthalten, nur als Abhängigkeit referenziert: die Node-Werkzeugkette von `skills/site-anatomy`
(Playwright, axe-core, designlang, colorthief, sharp, Lighthouse) — gepinnt in
`skills/site-anatomy/install/package.json` und `package-lock.json`, installiert per `install.sh`.
