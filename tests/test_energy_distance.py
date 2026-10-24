from Folder_All.ingestion.energy_base_distance import energy_base_distance


def test_identical_distributions_have_zero_energy_distance() -> None:
    samples = [[0.0, 1.0], [2.0, 3.0], [4.0, 5.0]]
    assert energy_base_distance(samples, samples) == 0.0


def test_separated_distributions_have_positive_energy_distance() -> None:
    left = [[0.0], [1.0], [2.0]]
    right = [[10.0], [11.0], [12.0]]
    assert energy_base_distance(left, right) > 0.0
