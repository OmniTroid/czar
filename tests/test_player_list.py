from tests.mock import MockClient

# PlayerStateObserver packet constants
PR_ADD = "0"
PR_REMOVE = "1"
PU_NAME = "0"
PU_CHARACTER = "1"
PU_CHARACTER_NAME = "2"
PU_AREA_ID = "3"


async def test_spectator_is_not_announced(test_server):
    """A joining spectator is hidden, so no PR packet goes out about them."""
    async with MockClient(test_server._test_host, test_server._test_port) as first:
        await first.handshake()

        async with MockClient(test_server._test_host, test_server._test_port) as second:
            await second.handshake()

            packets = await first.recv_all(timeout=0.3)
            assert all(cmd != "PR" for cmd, _ in packets)


async def test_character_select_announces_player(test_server):
    """Picking a character takes the player out of hiding and announces them."""
    async with MockClient(test_server._test_host, test_server._test_port) as first:
        await first.handshake()

        async with MockClient(test_server._test_host, test_server._test_port) as second:
            info = await second.handshake()
            await first.recv_all(timeout=0.2)

            await second.select_character(0)

            # First client receives PR#<id>#0 (ADD) about the second
            _, args = await first.recv_until("PR")
            assert args[0] == str(info["player_id"])
            assert args[1] == PR_ADD

            # Followed by the second client's player data
            updates = {}
            for _ in range(4):
                _, args = await first.recv_until("PU")
                assert args[0] == str(info["player_id"])
                updates[args[1]] = args[2]
            assert set(updates) == {PU_NAME, PU_CHARACTER, PU_CHARACTER_NAME, PU_AREA_ID}
            assert updates[PU_CHARACTER] == second.char_list[0]


async def test_new_player_receives_existing_players(test_server):
    """A joining player is handed the list of visible players during RD."""
    async with MockClient(test_server._test_host, test_server._test_port) as first:
        info = await first.handshake()
        await first.select_character(0)

        async with MockClient(test_server._test_host, test_server._test_port) as second:
            await second.send("HI", "test-hdid-2")
            await second.recv_until("ID")
            await second.send("ID", "AO2", "2.11.0")
            await second.recv_until("FL")
            await second.send("askchaa")
            await second.recv_until("SI")
            await second.send("RC")
            await second.recv_until("SC")
            await second.send("RM")
            await second.recv_until("SM")
            await second.send("RD")

            # The server sends the existing player list at the end of RD
            _, args = await second.recv_until("PR")
            assert args[0] == str(info["player_id"])
            assert args[1] == PR_ADD


async def test_disconnecting_player_is_removed(test_server):
    """A listed player disconnecting sends PR#<id>#1 (REMOVE) to the rest."""
    async with MockClient(test_server._test_host, test_server._test_port) as first:
        await first.handshake()
        await first.select_character(0)

        second = MockClient(test_server._test_host, test_server._test_port)
        await second.connect()
        info = await second.handshake()
        await second.select_character(1)

        # Drain the ADD/update packets about the second client
        await first.recv_all(timeout=0.2)

        await second.close()

        _, args = await first.recv_until("PR")
        assert args[0] == str(info["player_id"])
        assert args[1] == PR_REMOVE
