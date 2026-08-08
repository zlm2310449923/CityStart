# Role D Demo Script

1. Show the three-layer ArchiMate model and explain Business, Application and Technology layers.
2. Open P2 BPMN diagram and explain the housing subsidy application flow.
3. Open Housing Service Swagger at `http://127.0.0.1:8003/docs`.
4. Submit a housing subsidy application through `POST /housing-subsidy-applications`.
5. Add missing documents through `POST /housing-subsidy-applications/{application_id}/documents`.
6. Record parallel verification through `POST /housing-subsidy-applications/{application_id}/verification`.
7. Approve the application through `PATCH /housing-subsidy-applications/{application_id}/status`.
8. Show the P2 event log CSV and explain variants such as supplementary documents and verification failure.
