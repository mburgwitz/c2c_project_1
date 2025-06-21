import pytest

from basecar import BaseCar
from util.config.manager import ConfigManager

@pytest.fixture
def car():
    return BaseCar()

@pytest.mark.basecar
def test_speed(car):
    assert -100 == car.MIN_SPEED
    assert 100 == car.MAX_SPEED

    car.speed = -110
    assert car.speed == car.MIN_SPEED

    car.speed = -100
    assert car.speed == car.MIN_SPEED

    car.speed = 50
    assert car.speed == 50

    car.speed = 100
    assert car.speed == car.MAX_SPEED

    car.speed = 150
    assert car.speed == car.MAX_SPEED

@pytest.mark.basecar
def test_steering_angle(car):

    assert 45 == car.MIN_STEERING_ANGLE
    assert 135 == car.MAX_STEERING_ANGLE

    car.steering_angle = 35
    assert car.steering_angle == car.MIN_STEERING_ANGLE

    car.steering_angle = 45
    assert car.steering_angle == car.MIN_STEERING_ANGLE

    car.steering_angle = 50
    assert car.steering_angle == 50

    car.steering_angle = 135
    assert car.steering_angle == car.MAX_STEERING_ANGLE

    car.steering_angle = 150
    assert car.steering_angle == car.MAX_STEERING_ANGLE
        