import deliveryflow_agent_kernel
import deliveryflow_contracts
import deliveryflow_speccraft


def test_three_project_packages_are_importable() -> None:
    assert deliveryflow_contracts.__version__ == "0.1.0"
    assert deliveryflow_agent_kernel.__version__ == "0.1.0"
    assert deliveryflow_speccraft.__version__ == "0.1.0"
