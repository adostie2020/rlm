import unittest
from unittest.mock import MagicMock, patch

from rlm.environments.modal_repl import ModalREPL

class TestModalREPLPersistence(unittest.TestCase):
    @patch("rlm.environments.modal_repl.modal")
    @patch("rlm.environments.modal_repl.requests")
    def test_persistence_methods(self, mock_requests, mock_modal):
        # Setup mocks for Modal setup
        mock_app = MagicMock()
        mock_modal.App.lookup.return_value = mock_app
        
        mock_sandbox = MagicMock()
        mock_modal.Sandbox.create.return_value = mock_sandbox
        
        # Mock exec process (broker script)
        mock_process = MagicMock()
        mock_sandbox.exec.return_value = mock_process
        
        # Mock tunnels
        mock_sandbox.tunnels.return_value = {}

        # Initialize REPL with persistence=True
        repl = ModalREPL(persistent=True)
        
        # 1. Test initial state
        self.assertEqual(repl.get_context_count(), 0)
        self.assertEqual(repl.get_history_count(), 0)
        
        # Mock execute_code to avoid actual execution logic
        # We just want to verify it calls execute_code with the right scripts
        with patch.object(repl, "execute_code") as mock_execute:
            mock_execute.return_value = MagicMock(stderr="")
            
            # 2. Test add_context (auto-increment)
            idx1 = repl.add_context("test_context_1")
            self.assertEqual(idx1, 0)
            self.assertEqual(repl.get_context_count(), 1)
            
            # Verify script content
            call_args = mock_execute.call_args[0][0]
            self.assertIn("context_0 =", call_args)
            self.assertIn("context =", call_args) # Should alias context_0
            
            # 3. Test add_context (second context)
            idx2 = repl.add_context("test_context_2")
            self.assertEqual(idx2, 1)
            self.assertEqual(repl.get_context_count(), 2)
            
            call_args = mock_execute.call_args[0][0]
            self.assertIn("context_1 =", call_args)
            self.assertNotIn("context =", call_args) # Should NOT alias context_1
            
            # 4. Test add_history
            history = [{"role": "user", "content": "hi"}]
            idx_h1 = repl.add_history(history)
            self.assertEqual(idx_h1, 0)
            self.assertEqual(repl.get_history_count(), 1)
            
            call_args = mock_execute.call_args[0][0]
            self.assertIn("history_0 =", call_args)
            self.assertIn("history =", call_args) # Should alias history_0
            
            # 5. Test load_context (backward compatibility - forces index 0)
            repl.load_context("overwritten_context")
            # Should call add_context(..., 0)
            # Count remains max(2, 0+1) = 2
            self.assertEqual(repl.get_context_count(), 2)
            
            call_args = mock_execute.call_args[0][0]
            self.assertIn("context_0 =", call_args)
            
            # 6. Test update_handler_address
            new_addr = ("localhost", 9999)
            repl.update_handler_address(new_addr)
            self.assertEqual(repl.lm_handler_address, new_addr)

if __name__ == "__main__":
    unittest.main()
