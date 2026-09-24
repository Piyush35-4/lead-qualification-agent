from app.db.database import get_history, get_lead, save_message, update_lead


def test_create_update_and_history():
    lead = update_lead("lead-test", company="Acme", company_size=12)
    assert lead.company == "Acme"
    assert get_lead("lead-test").company_size == 12
    save_message("lead-test", "user", "Need a CRM")
    assert get_history("lead-test") == [{"role": "user", "content": "Need a CRM"}]
