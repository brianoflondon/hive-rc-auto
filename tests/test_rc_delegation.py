from hive_rc_auto.helpers.rc_delegation import mill

def test_mill():
    number = 33_000_000
    assert mill(number) == 33