((python-base-mode . ((dape-configs . (
                                       (ad-hoc-test
                                        modes (python-mode python-ts-mode)
                                        command "uv"
                                        command-args
                                        ("run" "python" "-m" "debugpy.adapter" "--port" :autoport)
                                        port :autoport
                                        :request "launch"
                                        :type "python"
                                        :env (:YANG_MODPATH (concat ".:" (dape-cwd) "yang-modules/ietf"))
                                        ;; :stopOnEntry t
                                        :cwd "."
                                        :program "test.py")
                                       (yangson
                                        modes (python-mode python-ts-mode)
                                        command "uv"
                                        command-args
                                        ("run" "python" "-m" "debugpy.adapter" "--port" :autoport)
                                        port :autoport
                                        :request "launch"
                                        :type "python"
                                        :env (:YANG_MODPATH (concat ".:" (dape-cwd) "yang-modules/ietf"))
                                        :cwd "."
                                        :program (concat (dape-cwd) "yangson")
                                       ))))))
