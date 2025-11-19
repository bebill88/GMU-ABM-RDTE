# RDT&E Entities Schema

| Column | Type | Description |
| --- | --- | --- |
| `entity_id` | string | Canonical organization/unit ID (e.g., `SRV-ARMY-XX-001`, `AGY-DIA-ISR`). |
| `name` | string | Full legal/operational name (e.g., “Army Futures Command ISR Team”). |
| `short_name` | string | Abbreviation (e.g., “AFC ISR”). |
| `entity_category` | string | Enum: `ServiceHQ`, `ProgramOffice`, `OperationalUnit`, `Agency`, `COCOM`, `FFRDC`, `Lab`, `PEO`, `JointTaskForce`, etc. |
| `service` | string | Service/component affiliation (Army, Navy, Air Force, USMC, USSF, DIA, NSA, NGA, Joint, etc.). |
| `parent_entity_id` | string | Optional parent organization ID for hierarchical roll-ups. |
| `has_organic_rdte` | integer | `1` if the entity executes RDT&E (engineering teams, labs); `0` otherwise. |
| `rdte_roles` | string | Semicolon-separated roles (sponsor;executing;requirements;test;ops). |
| `base_budget_type` | string | Primary appropriation (`MIP`, `NIP`, `TOA`, `O&M`, `RDT&E`, etc.). |
| `base_budget_pe` | string | Primary Program Element identifier funding the entity. |
| `base_budget_ba` | string | Budget Activity (BA2/BA3/BA4/BA5). |
| `estimated_rdte_capacity_musd` | number | Approximate annual RDT&E capacity ($M). |
| `estimated_rdte_staff` | integer | Staff headcount capable of executing RDT&E work. |
| `primary_domains` | string | Semicolon-separated domains (ISR;Cyber;AI;EW;Space;Maritime). |
| `authority_flags` | string | Statutory authorities (`10USC`, `50USC`, `22USC`, `Both`, etc.). |
| `location_region` | string | Regional alignment (CONUS-East, EUCOM, INDOPACOM, NCR, etc.). |
| `classification_band` | string | Dominant classification (UNCL, C-S, TS/SCI). |
| `notes` | string | Free-text context for analysts and non-technical readers. |

Use `docs/data_schema.md` and `data/program_org_links.csv` to bind these entities to programs so the GAO, vendor, shock, and collaboration pipelines share the same `entity_id` keys.

## Example rows

```
entity_id,name,short_name,entity_category,service,parent_entity_id,has_organic_rdte,rdte_roles,base_budget_type,base_budget_pe,base_budget_ba,estimated_rdte_capacity_musd,estimated_rdte_staff,primary_domains,authority_flags,location_region,classification_band,notes
SRV-ARMY-AFC-ISR,Army Futures Command ISR Team,AFC ISR,ProgramOffice,Army,SRV-ARMY-AFC,1,sponsor;executing;requirements,RDT&E,060XXX,BA4,50,75,ISR;AI,10USC,CONUS-Central,C-S,"ISR modernization program office with organic dev and experimentation capacity"
UNIT-USMC-INTBN-01,1st Intel Battalion RDT&E Cell,1st INTBn RDT&E,OperationalUnit,USMC,UNIT-USMC-1MEF,1,ops;requirements,TOA,,BA3,5,10,ISR;Cyber,10USC,INDOPACOM,C-S,"Operational unit with small RDT&E cell; base funding folded into larger battalion budget"
AGY-DIA-TECH,DIA Technical Collection Office,DIA TECH,Agency,DIA,AGY-DIA-HQ,1,sponsor;executing;requirements;test,MIP,060YYY,BA3,80,90,ISR;Space,50USC,NCR,TS-SCI,"MIP-funded intelligence tech office with authority to sponsor and execute RDT&E"
LAB-NAVY-NRL-ISR,Navy Research Lab ISR Division,NRL ISR,Lab,Navy,LAB-NAVY-NRL,1,executing;test,RDT&E,060ZZZ,BA4,120,150,ISR;EW,10USC,CONUS-East,C-S,"Core ISR lab; often executes work for multiple services and agencies"
```
