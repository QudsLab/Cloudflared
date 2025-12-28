//go:build windows

package main

import (
	"fmt"
	"syscall"
	"time"
	"unsafe"

	"github.com/pkg/errors"
	"github.com/urfave/cli/v2"
	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/svc"
	"golang.org/x/sys/windows/svc/eventlog"
	"golang.org/x/sys/windows/svc/mgr"

	"github.com/cloudflare/cloudflared/cmd/cloudflared/cliutil"
	"github.com/cloudflare/cloudflared/logger"
)

const (
	windowsServiceName        = "Cloudflared"
	windowsServiceDescription = "Cloudflared agent"
	windowsServiceUrl         = "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/configure-tunnels/local-management/as-a-service/windows/"

	recoverActionDelay      = time.Second * 20
	failureCountResetPeriod = time.Hour * 24

	serviceConfigFailureActionsFlag  = 4
	serviceControllerConnectionFailure = 1063

	LogFieldWindowsServiceName = "windowsServiceName"
)

func runApp(app *cli.App, graceShutdownC chan struct{}, args []string) {
	app.Commands = append(app.Commands, &cli.Command{
		Name:  "service",
		Usage: "Manages the cloudflared Windows service",
		Subcommands: []*cli.Command{
			{
				Name:   "install",
				Usage:  "Install cloudflared as a Windows service",
				Action: cliutil.ConfiguredAction(installWindowsService),
			},
			{
				Name:   "uninstall",
				Usage:  "Uninstall the cloudflared service",
				Action: cliutil.ConfiguredAction(uninstallWindowsService),
			},
		},
	})

	log := logger.Create(nil)

	isIntSess, err := svc.IsAnInteractiveSession()
	if err != nil {
		log.Fatal().Err(err).Msg("failed to determine if we are running in an interactive session")
	}
	if isIntSess {
		app.Run(args)
		return
	}

	err = svc.Run(windowsServiceName, &windowsService{app: app, graceShutdownC: graceShutdownC, args: args})
	if err != nil {
		if errno, ok := err.(syscall.Errno); ok && int(errno) == serviceControllerConnectionFailure {
			app.Run(args)
			return
		}
		log.Fatal().Err(err).Msgf("%s service failed", windowsServiceName)
	}
}

type windowsService struct {
	app            *cli.App
	graceShutdownC chan struct{}
	args           []string
}

func (s *windowsService) Execute(serviceArgs []string, r <-chan svc.ChangeRequest, statusChan chan<- svc.Status) (ssec bool, errno uint32) {
	log := logger.Create(nil)
	elog, err := eventlog.Open(windowsServiceName)
	if err != nil {
		log.Err(err).Msgf("Cannot open event log for %s", windowsServiceName)
		return
	}
	defer elog.Close()

	elog.Info(1, fmt.Sprintf("%s service starting", windowsServiceName))
	defer func() {
		elog.Info(1, fmt.Sprintf("%s service stopped", windowsServiceName))
	}()

	var args []string
	if len(serviceArgs) > 1 {
		args = serviceArgs
	} else {
		args = s.args
	}
	elog.Info(1, fmt.Sprintf("%s service arguments: %v", windowsServiceName, args))

	statusChan <- svc.Status{State: svc.StartPending}
	errC := make(chan error)
	go func() {
		errC <- s.app.Run(args)
	}()
	statusChan <- svc.Status{State: svc.Running, Accepts: svc.AcceptStop | svc.AcceptShutdown}

	for {
		select {
		case c := <-r:
			switch c.Cmd {
			case svc.Interrogate:
				statusChan <- c.CurrentStatus
			case svc.Stop, svc.Shutdown:
				if s.graceShutdownC != nil {
					elog.Info(1, "cloudflared starting graceful shutdown")
					close(s.graceShutdownC)
					s.graceShutdownC = nil
					statusChan <- svc.Status{State: svc.StopPending}
					continue
				}
				elog.Info(1, "cloudflared terminating immediately")
				statusChan <- svc.Status{State: svc.StopPending}
				return false, 0
			default:
				elog.Error(1, fmt.Sprintf("unexpected control request #%d", c))
			}
		case err := <-errC:
			if err != nil {
				elog.Error(1, fmt.Sprintf("cloudflared terminated with error %v", err))
				ssec = true
				errno = 1
			} else {
				elog.Info(1, "cloudflared terminated without error")
				errno = 0
			}
			return
		}
	}
}

func installWindowsService(c *cli.Context) error {
	zeroLogger := logger.CreateLoggerFromContext(c, logger.EnableTerminalLog)

	zeroLogger.Info().Msg("Installing cloudflared Windows service")
	exepath, err := os.Executable()
	if err != nil {
		return errors.Wrap(err, "Cannot find path name that start the process")
	}
	m, err := mgr.Connect()
	if err != nil {
		return errors.Wrap(err, "Cannot establish a connection to the service control manager")
	}
	defer m.Disconnect()
	s, err := m.OpenService(windowsServiceName)
	log := zeroLogger.With().Str(LogFieldWindowsServiceName, windowsServiceName).Logger()
	if err == nil {
		s.Close()
		return errors.New(serviceAlreadyExistsWarn(windowsServiceName))
	}
	extraArgs, err := getServiceExtraArgsFromCliArgs(c, &log)
	if err != nil {
		errMsg := "Unable to determine extra arguments for windows service"
		log.Err(err).Msg(errMsg)
		return errors.Wrap(err, errMsg)
	}

	config := mgr.Config{StartType: mgr.StartAutomatic, DisplayName: windowsServiceDescription}
	s, err = m.CreateService(windowsServiceName, exepath, config, extraArgs...)
	if err != nil {
		return errors.Wrap(err, "Cannot install service")
	}
	defer s.Close()
	log.Info().Msg("cloudflared agent service is installed")
	err = eventlog.InstallAsEventCreate(windowsServiceName, eventlog.Error|eventlog.Warning|eventlog.Info)
	if err != nil {
		s.Delete()
		return errors.Wrap(err, "Cannot install event logger")
	}

	err = configRecoveryOption(s.Handle)
	if err != nil {
		log.Err(err).Msg("Cannot set service recovery actions")
		log.Info().Msgf("See %s to manually configure service recovery actions", windowsServiceUrl)
	}

	err = s.Start()
	if err == nil {
		log.Info().Msg("Agent service for cloudflared installed successfully")
	}
	return err
}

func uninstallWindowsService(c *cli.Context) error {
	log := logger.CreateLoggerFromContext(c, logger.EnableTerminalLog).
		With().
		Str(LogFieldWindowsServiceName, windowsServiceName).Logger()

	log.Info().Msg("Uninstalling cloudflared agent service")
	m, err := mgr.Connect()
	if err != nil {
		return errors.Wrap(err, "Cannot establish a connection to the service control manager")
	}
	defer m.Disconnect()
	s, err := m.OpenService(windowsServiceName)
	if err != nil {
		return fmt.Errorf("agent service %s is not installed, so it could not be uninstalled", windowsServiceName)
	}
	defer s.Close()

	if status, err := s.Query(); err == nil && status.State == svc.Running {
		log.Info().Msg("Stopping cloudflared agent service")
		if _, err := s.Control(svc.Stop); err != nil {
			log.Info().Err(err).Msg("Failed to stop cloudflared agent service, you may need to stop it manually to complete uninstall.")
		}
	}

	err = s.Delete()
	if err != nil {
		return errors.Wrap(err, "Cannot delete agent service")
	}
	log.Info().Msg("Agent service for cloudflared was uninstalled successfully")
	err = eventlog.Remove(windowsServiceName)
	if err != nil {
		return errors.Wrap(err, "Cannot remove event logger")
	}
	return nil
}

type scAction int

const (
	scActionNone scAction = iota
	scActionRestart
	scActionReboot
	scActionRunCommand
)

type serviceFailureActions struct {
	resetPeriod uint32
	rebootMsg   *uint16
	command     *uint16
	actionCount uint32
	actions     uintptr
}

type serviceFailureActionsFlag struct {
	enableActionsForStopsWithErr int
}

type recoveryAction struct {
	recoveryType uint32
	delay        uint32
}

func configRecoveryOption(handle windows.Handle) error {
	actions := []recoveryAction{
		{recoveryType: uint32(scActionRestart), delay: uint32(recoverActionDelay / time.Millisecond)},
	}
	serviceRecoveryActions := serviceFailureActions{
		resetPeriod: uint32(failureCountResetPeriod / time.Second),
		actionCount: uint32(len(actions)),
		actions:     uintptr(unsafe.Pointer(&actions[0])),
	}
	if err := windows.ChangeServiceConfig2(handle, windows.SERVICE_CONFIG_FAILURE_ACTIONS, (*byte)(unsafe.Pointer(&serviceRecoveryActions))); err != nil {
		return err
	}
	serviceFailureActionsFlag := serviceFailureActionsFlag{enableActionsForStopsWithErr: 1}
	return windows.ChangeServiceConfig2(handle, serviceConfigFailureActionsFlag, (*byte)(unsafe.Pointer(&serviceFailureActionsFlag)))
}
